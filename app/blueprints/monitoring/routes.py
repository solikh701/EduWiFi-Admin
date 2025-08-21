import math
from datetime import date, datetime

from flask import jsonify, request
from sqlalchemy import text, func

from . import monitoring_bp
from ...extensions import moni_db, db
from ...models import User
from ...logging_config import configure_logging

logger = configure_logging()


@monitoring_bp.route("/api/monitoring", methods=["GET"])
def api_monitoring():
    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = int(request.args.get("limit", 20))
        limit = 10 if limit < 10 else (100 if limit > 100 else limit)

        search = (request.args.get("search", "") or "").strip()

        allowed_sort = {
            "id": "id",
            "ts": "ts",
            "client_ip": "client_ip",
            "mac": "mac",
            "hostname": "hostname",
            "domain": "domain",
            "protocol": "protocol",
            "fio": "fio",
            "phone_number": "phone_number",
        }
        sort = request.args.get("sort", "id")
        sort_col = allowed_sort.get(sort, "id")

        order = request.args.get("order", "desc").lower()
        order_sql = "ASC" if order == "asc" else "DESC"

        offset = (page - 1) * limit

        where_clause = ""
        params = {}
        if search:
            where_clause = (
                "WHERE client_ip LIKE :q OR mac LIKE :q OR hostname LIKE :q "
                "OR domain LIKE :q OR protocol LIKE :q"
            )
            params["q"] = f"%{search}%"

        with moni_db.connect() as conn:
            total_sql = text(f"SELECT COUNT(*) AS cnt FROM monitoring {where_clause}")
            total = conn.execute(total_sql, params).scalar() or 0

            data_sql = text(f"""
                SELECT
                    id,
                    DATE_FORMAT(ts, '%Y-%m-%d %H:%i:%s') AS ts,
                    client_ip,
                    UPPER(mac) AS mac,
                    hostname,
                    domain,
                    protocol
                FROM monitoring
                {where_clause}
                ORDER BY {sort_col} {order_sql}
                LIMIT :limit OFFSET :offset
            """)
            params.update({"limit": limit, "offset": offset})
            rows = conn.execute(data_sql, params).mappings().all()

        items = []
        mac_set = set()
        for r in rows:
            d = dict(r)
            if isinstance(d.get("ts"), (datetime, date)):
                d["ts"] = d["ts"].strftime("%Y-%m-%d %H:%M:%S")
            if d.get("mac"):
                d["mac"] = str(d["mac"]).upper()
                mac_set.add(d["mac"])
            items.append(d)

        user_map = {}
        if mac_set:
            q_users = (
                db.session.query(User.MAC, User.fio, User.phone_number)
                .filter(func.upper(User.MAC).in_(mac_set))
                .all()
            )
            user_map = {
                (u[0] or "").upper(): {"fio": u[1], "phone_number": u[2]} 
                for u in q_users
            }

        for d in items:
            u = user_map.get((d.get("mac") or "").upper())
            d["fio"] = u["fio"] if u else "-"
            d["phone_number"] = u["phone_number"] if u else "-"

        pages = max(1, math.ceil(total / limit)) if limit else 1

        return jsonify({
            "page": page,
            "limit": limit,
            "total": total,
            "pages": pages,
            "has_prev": page > 1,
            "has_next": page < pages,
            "sort": sort_col,
            "order": order_sql,
            "items": items,
        })

    except Exception as e:
        logger.exception("Monitoring API error")
        return jsonify({"error": str(e)}), 500
