from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import urlparse

from flask import jsonify, request
from sqlalchemy import asc, desc, or_

from . import teachers_bp
from ...models import User
from ...extensions import cache, limiter

logger = logging.getLogger("app.teachers")

_UNI_CACHE_TTL = 300
_TEACHERS_TTL  = 30


def _extract_site_from_link(link: str) -> str | None:
    if not link:
        return None
    try:
        parsed = urlparse(link)
        host = parsed.hostname or ""
        if not host and "://" not in link:
            host = urlparse("http://" + link).hostname or ""
        if not host:
            return None
        parts = host.split(".")
        if len(parts) >= 2:
            return parts[-2].lower()
        return host.lower()
    except Exception as e:
        logger.warning("link_login parse failed: %s (%s)", link, e)
        return None


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@teachers_bp.route("/api/teachers/universities", methods=["GET"])
@limiter.limit("30 per minute")
def teacher_universities():
    cache_key = "teachers:universities:v1"
    cached = cache.get(cache_key)
    if cached is not None:
        return jsonify(cached), 200

    try:
        rows: Iterable[Tuple[str]] = (
            User.query
            .with_entities(User.link_login)
            .filter(User.link_login.isnot(None), User.link_login != "")
            .all()
        )

        unique_sites = set()
        for (link,) in rows:
            site = _extract_site_from_link(link)
            if site:
                unique_sites.add(site)

        result = {"universities": sorted(unique_sites)}
        cache.set(cache_key, result, timeout=_UNI_CACHE_TTL)
        return jsonify(result), 200

    except Exception:
        logger.exception("teacher_universities failed")
        return jsonify({"universities": []}), 500


def _teachers_allowed_sort() -> Dict[str, Any]:
    return {
        "id": User.id,
        "mac": User.MAC,
        "fio": User.fio,
        "phone": User.phone_number,
        "university": User.link_login,
    }


@cache.memoize(timeout=_TEACHERS_TTL)
def _teachers_list_data(page: int, limit: int, sort: str, order: str, uni: str, q: str) -> Dict[str, Any]:
    query = (
        User.query
        .filter(User.role.isnot(None))
        .filter(User.role.ilike("teacher"))
    )

    if uni and uni != "off":
        query = query.filter(
            User.link_login.isnot(None),
            User.link_login != "",
            User.link_login.ilike(f"%{_escape_like(uni)}%", escape="\\"),
        )
        
    if q:
        like = f"%{_escape_like(q)}%"
        query = query.filter(
            or_(
                User.MAC.ilike(like, escape="\\"),
                User.fio.ilike(like, escape="\\"),
                User.phone_number.ilike(like, escape="\\"),
                User.link_login.ilike(like, escape="\\"),
                User.role.ilike(like, escape="\\"),
            )
        )

    total = query.order_by(None).count()

    sortmap = _teachers_allowed_sort()
    col = sortmap.get(sort, User.id)
    query_sorted = query.order_by(desc(col) if order == "desc" else asc(col))

    rows: List[Tuple[int, str, str, str, str, str]] = (
        query_sorted
        .with_entities(User.id, User.MAC, User.fio, User.phone_number, User.role, User.link_login)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = []
    for _id, mac, fio, phone, role, link_login in rows:
        uni_name = _extract_site_from_link(link_login) if link_login else None
        items.append({
            "id": _id,
            "mac": mac,
            "fio": fio,
            "phone_number": phone,
            "role": role,
            "university": uni_name or "-",
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@teachers_bp.route("/api/teachers", methods=["GET"])
@limiter.limit("120 per minute")
def teachers_list():
    try:
        try:
            page = int(request.args.get("page", 1))
        except (TypeError, ValueError):
            page = 1
        try:
            limit = int(request.args.get("limit", 20))
        except (TypeError, ValueError):
            limit = 20

        page = max(page, 1)
        limit = min(max(limit, 1), 200)

        sort = (request.args.get("sort") or "id").lower()
        if sort not in _teachers_allowed_sort():
            sort = "id"

        order = (request.args.get("order") or "desc").lower()
        if order not in ("asc", "desc"):
            order = "desc"

        uni = (request.args.get("university") or "off").strip().lower()
        q = (request.args.get("q") or "").strip()

        data = _teachers_list_data(page, limit, sort, order, uni, q)
        return jsonify(data), 200

    except Exception:
        logger.exception("teachers_list failed")
        return jsonify({"items": [], "total": 0, "page": 1, "limit": 20, "pages": 0}), 500
