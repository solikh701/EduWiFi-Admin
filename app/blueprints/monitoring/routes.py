import math
from . import monitoring_bp
from sqlalchemy import text
from ...extensions import moni_db
from flask import jsonify, request
from datetime import date, datetime
from ...logging_config import configure_logging


logger = configure_logging()


@monitoring_bp.route("/api/monitoring", methods=["GET"])
def api_monitoring():
    """
    Query params:
      - page: int >=1
      - limit: int (10/20/50/100)
      - search: str
      - sort: one of ['id','ts','client_ip','mac','hostname','domain','protocol','uid']
      - order: 'asc' | 'desc'
    """
    try:
        # --- Params ---
        page  = max(1, int(request.args.get("page", 1)))
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
            "uid": "uid",
        }
        sort = request.args.get("sort", "id")
        sort_col = allowed_sort.get(sort, "id")

        order = request.args.get("order", "desc").lower()
        order_sql = "ASC" if order == "asc" else "DESC"

        offset = (page - 1) * limit

        # --- WHERE (search) ---
        where_clause = ""
        params = {}
        if search:
            where_clause = (
                "WHERE client_ip LIKE :q OR mac LIKE :q OR hostname LIKE :q "
                "OR domain LIKE :q OR protocol LIKE :q OR uid LIKE :q"
            )
            params["q"] = f"%{search}%"

        # --- Query ---
        with moni_db.connect() as conn:
            # total count (search bo'yicha ham)
            total_sql = text(f"SELECT COUNT(*) AS cnt FROM monitoring {where_clause}")
            total = conn.execute(total_sql, params).scalar() or 0

            # Ma'lumotlar (MAC uppercase; ts ni string formatda qaytaramiz)
            # Agar ts DATETIME bo'lsa, DATE_FORMAT dan foydalanamiz
            # ORDER BY - faqat ruxsat berilgan ustunlarda
            data_sql = text(f"""
                SELECT
                    id,
                    DATE_FORMAT(ts, '%Y-%m-%d %H:%i:%s') AS ts,
                    client_ip,
                    UPPER(mac) AS mac,
                    hostname,
                    domain,
                    protocol,
                    uid
                FROM monitoring
                {where_clause}
                ORDER BY {sort_col} {order_sql}
                LIMIT :limit OFFSET :offset
            """)
            params.update({"limit": limit, "offset": offset})
            rows = conn.execute(data_sql, params).mappings().all()

        # JSON-da datetime yo'q, lekin baribir himoya: (kutilmagan tip bo'lsa str ga aylantiramiz)
        items = []
        for r in rows:
            d = dict(r)
            ts_val = d.get("ts")
            if isinstance(ts_val, (datetime, date)):
                d["ts"] = ts_val.strftime("%Y-%m-%d %H:%M:%S")
            # MAC yuqorida UPPER qilingan; shunchaki string bo'lsa ham xavfsiz
            if d.get("mac"):
                d["mac"] = str(d["mac"]).upper()
            items.append(d)

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
