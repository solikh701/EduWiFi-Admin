from . import teachers_bp
from ...models import User
from app.extensions import cache
from urllib.parse import urlparse
from flask import jsonify, request
from sqlalchemy import asc, desc, or_
from ...logging_config import configure_logging

logger = configure_logging()

def _extract_site_from_link(link: str) -> str | None:
    if not link:
        return None
    try:
        host = urlparse(link).netloc or link
        host = host.split('/')[0].split(':')[0]
        parts = host.split('.')
        if len(parts) >= 2:
            return parts[-2].lower() 
    except Exception as e:
        logger.warning(f"link_login parse failed: {link} ({e})")
    return None

@teachers_bp.route('/api/teachers/universities', methods=['GET'])
def teacher_universities():
    try:
        rows = (User.query
                .with_entities(User.link_login)
                .filter(User.link_login.isnot(None), User.link_login != '')
                .all())

        unique_sites = set()
        for (link,) in rows:
            site = _extract_site_from_link(link)
            if site:
                unique_sites.add(site)

        return jsonify({"universities": sorted(unique_sites)}), 200
    except Exception:
        logger.exception("teacher_universities failed")
        return jsonify({"universities": []}), 500


@teachers_bp.route('/api/teachers', methods=['GET'])
@cache.cached(timeout=2, query_string=True)
def teachers_list():
    try:
        page  = max(int(request.args.get('page', 1)), 1)
        limit = min(max(int(request.args.get('limit', 20)), 1), 200)
        sort  = (request.args.get('sort') or 'id').lower()
        order = (request.args.get('order') or 'desc').lower()
        uni   = (request.args.get('university') or 'off').strip().lower()
        q     = (request.args.get('q') or '').strip()

        base = User.query.filter(User.role.isnot(None)).filter(User.role.ilike('teacher'))

        # Universitet bo'yicha filter
        if uni and uni != 'off':
            base = base.filter(
                User.link_login.isnot(None),
                User.link_login != '',
                User.link_login.ilike(f"%{uni}%")
            )

        # Qidiruv (MAC, FIO, telefon, link_login, role)
        if q:
            like = f"%{q}%"
            base = base.filter(or_(
                User.MAC.ilike(like),
                User.fio.ilike(like),
                User.phone_number.ilike(like),
                User.link_login.ilike(like),
                User.role.ilike(like),
            ))

        sortmap = {
            "id": User.id,
            "mac": User.MAC,
            "fio": User.fio,
            "phone": User.phone_number,
            "university": User.link_login
        }
        col = sortmap.get(sort, User.id)
        base = base.order_by(desc(col) if order == 'desc' else asc(col))

        total = base.count()
        rows = base.offset((page - 1) * limit).limit(limit).all()

        items = []
        for u in rows:
            uni_name = _extract_site_from_link(u.link_login) if u.link_login else None
            items.append({
                "id": u.id,
                "mac": u.MAC,
                "fio": u.fio,
                "phone_number": u.phone_number,
                "role": u.role,
                "university": uni_name or "-"
            })

        return jsonify({
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }), 200
    except Exception:
        logger.exception("teachers_list failed")
        return jsonify({"items": [], "total": 0, "page": 1, "limit": 20, "pages": 0}), 500
