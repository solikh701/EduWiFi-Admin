from __future__ import annotations

import logging
from typing import Any, Optional

from flask import jsonify, request

from . import tariff_bp
from ...extensions import db, cache, limiter
from ...models import tariff_plan
from ...functions import get_radius_plans, update_tarif_tables

logger = logging.getLogger("app.tariff")

_TARIFFS_CACHE_KEY = "tariffs:plans:v1"
_TARIFFS_TTL = 30 


def _to_bool(val: Any, default: Optional[bool] = None) -> Optional[bool]:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int,)):
        return bool(val)
    if isinstance(val, str):
        v = val.strip().lower()
        if v in ("1", "true", "on", "yes"):
            return True
        if v in ("0", "false", "off", "no"):
            return False
    return default


def _parse_duration_days(payload_val, current_val):
    def _num_or_none(v):
        try:
            if v is None:
                return None
            if isinstance(v, (int,)):
                return int(v)
            s = str(v).strip()
            if s.isdigit():
                return int(s)
        except Exception:
            return None
        return None

    cand = _num_or_none(payload_val)
    if cand is not None:
        return cand
    return current_val


@tariff_bp.route("/api/tarif_plans", methods=["GET"])
@limiter.limit("60 per minute")
def get_tarif_plans_route():
    try:
        cached = cache.get(_TARIFFS_CACHE_KEY)
        if cached is not None:
            return jsonify(cached), 200

        plans = tariff_plan.query.all()
        local_list = [plan.to_dict() for plan in plans]

        radius_data = get_radius_plans()

        response = {
            "local_plans": local_list,
            "radius_plans": radius_data,
        }

        cache.set(_TARIFFS_CACHE_KEY, response, timeout=_TARIFFS_TTL)
        return jsonify(response), 200

    except Exception as e:
        logger.exception("get_tarif_plans_route failed: %s", e)
        return jsonify({"error": "An error occurred"}), 500


@tariff_bp.route("/api/tarif_plans", methods=["POST"])
@limiter.limit("20 per minute")
def update_tarif_plans():
    data = request.get_json(silent=True) or {}

    try:
        items = data["tarifData"]

        bepul_timeout = bepul_rate = bepul_total = None
        kun_timeout = kun_rate = kun_total = None
        hafta_timeout = hafta_rate = hafta_total = None
        oy_timeout = oy_rate = oy_total = None

        changed = False

        for tarif in items:
            plan_id = tarif.get("id")
            if plan_id is None:
                continue

            plan = db.session.get(tariff_plan, plan_id)
            if not plan:
                logger.warning("[update_tarif_plans] Plan ID %s not found", plan_id)
            else:
                if "price" in tarif:
                    try:
                        plan.price = tarif.get("price", plan.price)
                    except Exception:
                        pass

                if "is_active" in tarif:
                    ia = _to_bool(tarif.get("is_active"), default=plan.is_active)
                    if ia is not None:
                        plan.is_active = ia

                new_duration = _parse_duration_days(
                    tarif.get("duration_days", tarif.get("name")), plan.duration_days
                )
                plan.duration_days = new_duration

                existing_rate = tarif.get("rate_limit_db")
                plan.rate_limit = tarif.get("rate_limit", existing_rate) or plan.rate_limit

                changed = True

                logger.info(
                    "[update_tarif_plans] Updated plan ID %s: price=%s, active=%s, duration=%s, rate=%s",
                    plan_id, plan.price, plan.is_active, plan.duration_days, plan.rate_limit
                )

            session_timeout = tarif.get("session_timeout_seconds")
            mikrotik_rate = tarif.get("rate_limit_db")
            mikrotik_total = tarif.get("session_total_bytes")

            if plan_id == 1:
                bepul_timeout, bepul_rate, bepul_total = session_timeout, mikrotik_rate, mikrotik_total
            elif plan_id == 2:
                kun_timeout, kun_rate, kun_total = session_timeout, mikrotik_rate, mikrotik_total
            elif plan_id == 3:
                hafta_timeout, hafta_rate, hafta_total = session_timeout, mikrotik_rate, mikrotik_total
            elif plan_id == 4:
                oy_timeout, oy_rate, oy_total = session_timeout, mikrotik_rate, mikrotik_total

        if changed:
            db.session.commit()

        update_tarif_tables(
            bepul_timeout, bepul_rate, bepul_total,
            kun_timeout,   kun_rate,   kun_total,
            hafta_timeout, hafta_rate, hafta_total,
            oy_timeout,    oy_rate,    oy_total
        )

        cache.delete(_TARIFFS_CACHE_KEY)

    except Exception as e:
        db.session.rollback()
        logger.error("[update_tarif_plans] Error updating tariff plans: %s", e)
        return jsonify({"error": "Update failed"}), 500

    return jsonify({"message": "Tarif plans updated successfully"}), 200
