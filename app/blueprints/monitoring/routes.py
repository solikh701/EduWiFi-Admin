import math
from datetime import datetime, timedelta

from flask import jsonify, request
from sqlalchemy import func

from . import monitoring_bp
from ...extensions import monitoring_coll, db
from ...models import User
from ...logging_config import configure_logging

logger = configure_logging()
LOCAL_OFFSET_HOURS = 0


def fmt_ts_local(dt):
    if isinstance(dt, (datetime,)):
        return (dt + timedelta(hours=LOCAL_OFFSET_HOURS)).strftime("%Y-%m-%d %H:%M:%S")
    return dt

@monitoring_bp.route("/api/monitoring", methods=["GET"])
def api_monitoring():
    try:
        page = max(1, int(request.args.get("page", 1)))
        limit = int(request.args.get("limit", 20))
        limit = 10 if limit < 10 else (100 if limit > 100 else limit)
        offset = (page - 1) * limit

        search = (request.args.get("search", "") or "").strip()

        allowed_sort = {
            "id": "_id",
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
        sort_field = allowed_sort.get(sort, "_id")

        order = request.args.get("order", "desc").lower()
        sort_dir = 1 if order == "asc" else -1

        filt = {}
        if search:
            filt = {
                "$or": [
                    {"client_ip": {"$regex": search, "$options": "i"}},
                    {"mac":       {"$regex": search, "$options": "i"}},
                    {"hostname":  {"$regex": search, "$options": "i"}},
                    {"domain":    {"$regex": search, "$options": "i"}},
                    {"protocol":  {"$regex": search, "$options": "i"}},
                ]
            }

        total = monitoring_coll.count_documents(filt)

        cursor = monitoring_coll.find(
            filt,
            sort=[(sort_field, sort_dir)],
            skip=offset,
            limit=limit
        )

        items = []
        mac_set = set()

        seq_id = offset + 1
        for doc in cursor:
            d = {
                "id": seq_id,
                "ts": fmt_ts_local(doc.get("ts")),
                "client_ip": doc.get("client_ip"),
                "mac": (doc.get("mac") or ""),
                "hostname": doc.get("hostname"),
                "domain": doc.get("domain"),
                "protocol": doc.get("protocol"),
                "uid": doc.get("uid"),
            }
            if d["mac"]:
                d["mac"] = d["mac"].upper()
                mac_set.add(d["mac"])
            items.append(d)
            seq_id += 1

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
            u = user_map.get(d.get("mac",""))
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
            "sort": sort_field,
            "order": "ASC" if sort_dir == 1 else "DESC",
            "items": items,
        })

    except Exception as e:
        logger.exception("Monitoring API error")
        return jsonify({"error": str(e)}), 500
