import math
from . import monitoring_bp
from sqlalchemy import text
from ...extensions import moni_db
from flask import jsonify, request
from ...logging_config import configure_logging


logger = configure_logging()


@monitoring_bp.route("/api/monitoring", methods=["GET"])
def get_monitoring_data():
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))
        search = request.args.get("search", "").strip()
        sort = request.args.get("sort", "id")
        order = request.args.get("order", "desc")

        offset = (page - 1) * limit

        where_clause = ""
        params = {}
        if search:
            where_clause = """
            WHERE client_ip LIKE :q OR mac LIKE :q OR hostname LIKE :q OR domain LIKE :q OR protocol LIKE :q OR uid LIKE :q
            """
            params["q"] = f"%{search}%"

        with moni_db.connect() as conn:
            total_query = text(f"SELECT COUNT(*) as cnt FROM monitoring {where_clause}")
            total = conn.execute(total_query, params).scalar() or 0

            allowed_sort = ["id", "ts", "client_ip", "mac", "hostname", "domain", "protocol", "uid"]
            if sort not in allowed_sort:
                sort = "id"
            order_sql = "ASC" if order.lower() == "asc" else "DESC"

            query = text(f"""
                SELECT id, ts, client_ip, mac, hostname, domain, protocol, uid
                FROM zeekdb.monitoring
                {where_clause}
                ORDER BY {sort} {order_sql}
                LIMIT :limit OFFSET :offset
            """)
            params.update({"limit": limit, "offset": offset})
            rows = conn.execute(query, params).mappings().all()

        return jsonify({
            "page": page,
            "limit": limit,
            "total": total,
            "pages": math.ceil(total / limit),
            "items": [dict(r) for r in rows]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
