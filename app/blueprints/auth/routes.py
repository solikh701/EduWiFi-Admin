from __future__ import annotations

import logging
from decimal import Decimal
from typing import Dict, Any, Iterable, Tuple
from urllib.parse import urlparse

from flask import request, jsonify
from sqlalchemy import text

from . import auth_bp
from ...extensions import db, cache, limiter
from ...models import User, Transaction
from werkzeug.exceptions import RequestEntityTooLarge

try:
    from ...env import users as env_users
except Exception:
    env_users = {"admin": "admin", "password": "admin"}

logger = logging.getLogger("app.auth")

_DASHBOARD_CACHE_KEY = "dashboard:v1"
_DASHBOARD_TTL = 30 


def _to_number(v):
    if v is None:
        return 0
    if isinstance(v, Decimal):
        return float(v)
    return v


def _sld_from_url(url: str) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).hostname
        if not host and "://" not in url:
            host = urlparse("http://" + url).hostname
        if not host:
            return None
        parts = host.split(".")
        if len(parts) >= 2:
            return parts[-2]
        return host
    except Exception:
        return None


@auth_bp.errorhandler(RequestEntityTooLarge)
def handle_large_request(e):
    return jsonify({"error": "File size exceeds the allowed limit of 500 MB."}), 413


@auth_bp.route("/api/login", methods=["POST"])
@limiter.limit("8 per minute; 40 per hour")
def login():
    data = request.get_json(silent=True) or {}
    login_name = (data.get("login") or "").strip()
    password = data.get("password") or ""

    logger.debug("[login] Attempted login with login=%s", login_name)

    if login_name == env_users.get("admin") and password == env_users.get("password"):
        logger.info("[login] Admin login successful")
        return jsonify({"success": True}), 200

    logger.warning("[login] Invalid login attempt: login=%s", login_name)
    return jsonify({"success": False, "message": "Invalid login or password"}), 400


@auth_bp.route("/api/dashboard", methods=["GET"])
@limiter.limit("30 per minute")  # Juda ko'p so'rovlar bo'lsa ham Redis bilan arzon
def dashboard_data():
    cached = cache.get(_DASHBOARD_CACHE_KEY)
    if cached is not None:
        return jsonify(cached)

    total_connections = db.session.execute(
        text("SELECT COUNT(*) FROM user_authorization")
    ).scalar() or 0

    user_rows: Iterable[Tuple[str, str]] = db.session.execute(
        text(
            """
            SELECT phone_number, link_login
            FROM user
            WHERE link_login IS NOT NULL AND link_login != ''
            """
        )
    ).fetchall()

    phone_to_domain: Dict[str, str] = {}
    wifi_domains = set()
    for phone_number, link in user_rows:
        dom = _sld_from_url(link)
        if dom:
            phone_to_domain[str(phone_number)] = dom
            wifi_domains.add(dom)
    total_wifi = len(wifi_domains)

    monthly_income = _to_number(
        db.session.execute(
            text(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM transaction
                WHERE create_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                """
            )
        ).scalar()
    )

    connections_by_month_rows: Iterable[Tuple[str, int]] = db.session.execute(
        text(
            """
            SELECT DATE_FORMAT(authorization_date, '%Y-%m') AS ym, COUNT(*) AS cnt
            FROM user_authorization
            WHERE authorization_date >= DATE_SUB(CURDATE(), INTERVAL 11 MONTH)
            GROUP BY ym
            ORDER BY ym
            """
        )
    ).fetchall()
    ym_to_count = {ym: int(cnt) for ym, cnt in connections_by_month_rows}

    from datetime import date

    def last_12_month_keys():
        y = date.today().year
        m = date.today().month
        keys = []
        for _ in range(12):
            keys.append(f"{y:04d}-{m:02d}")
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        keys.reverse()
        return keys

    connections_chart = [ym_to_count.get(k, 0) for k in last_12_month_keys()]

    tx_sum_rows: Iterable[Tuple[str, Decimal]] = db.session.execute(
        text(
            """
            SELECT phone_number, COALESCE(SUM(amount), 0) AS total
            FROM transaction
            GROUP BY phone_number
            """
        )
    ).fetchall()

    domain_income: Dict[str, float] = {}
    for phone_number, total in tx_sum_rows:
        dom = phone_to_domain.get(str(phone_number))
        if not dom:
            continue
        domain_income[dom] = domain_income.get(dom, 0.0) + float(_to_number(total))

    wifi_income_data = [{"name": dom, "value": amt} for dom, amt in domain_income.items()]

    new_users = User.query.order_by(User.id.desc()).limit(5).all()
    new_accounts_data = [
        {
            "id": u.id,
            "date": str(u.authorizations[-1].authorization_date) if getattr(u, "authorizations", None) else "",
            "user": getattr(u, "fio", ""),
            "account": "Verified" if not getattr(u, "block", False) else "Blocked",
            "username": getattr(u, "phone_number", ""),
        }
        for u in new_users
    ]

    recent_transactions = Transaction.query.order_by(Transaction.id.desc()).limit(5).all()
    recent_transactions_data = [
        {
            "id": t.id,
            "date": str(getattr(t, "create_time", "")),
            "amount": _to_number(getattr(t, "amount", 0)),
            "status": getattr(t, "status", ""),
            "desc": getattr(t, "reason", ""),
        }
        for t in recent_transactions
    ]

    result: Dict[str, Any] = {
        "total_connections": int(total_connections),
        "total_wifi": int(total_wifi),
        "monthly_income": _to_number(monthly_income),
        "connections_chart": connections_chart,
        "wifi_income_data": wifi_income_data,
        "new_accounts": new_accounts_data,
        "recent_transactions": recent_transactions_data,
    }

    # Redis keshga yozamiz
    cache.set(_DASHBOARD_CACHE_KEY, result, timeout=_DASHBOARD_TTL)
    return jsonify(result)
