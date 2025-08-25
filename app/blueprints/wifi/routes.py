import re
from . import wifi_bp
from decimal import Decimal
from ...extensions import db
from urllib.parse import urlparse
from flask import jsonify, request
from datetime import date, timedelta
from sqlalchemy import func, text, asc, desc
from ...logging_config import configure_logging
from ...models import User, Transaction, UserAuthorization

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


def _extract_host(link: str) -> str | None:
    if not link:
        return None
    try:
        host = urlparse(link).netloc or link
        return host.split('/')[0].split(':')[0].lower()
    except Exception:
        return None


def _collect_university_users(university_name: str):
    """Universitetga tegishli userlar ro‘yxati (id, mac, phone, fio, role, link_login, host)"""
    name = (university_name or '').lower().strip()
    if not name:
        return []

    # Keng qamrovli LIKE, keyin Python bilan aniq tekshiramiz
    guess = f"%{name}%"
    rows = (
        db.session.query(User.id, User.MAC, User.phone_number, User.fio, User.role, User.link_login)
        .filter(User.link_login.isnot(None), User.link_login != '')
        .filter(User.link_login.ilike(guess))
        .all()
    )

    result = []
    for uid, mac, phone, fio, role, link in rows:
        site = _extract_site_from_link(link)
        if site == name:
            result.append({
                "id": uid, "mac": mac, "phone": phone, "fio": fio,
                "role": role, "link": link, "host": _extract_host(link)
            })
    return result

def _parse_amount(v) -> int:
    if v is None:
        return 0
    if isinstance(v, (int, float, Decimal)):
        try:
            return int(v)
        except Exception:
            return int(float(v))
    s = re.sub(r"[^\d]", "", str(v))
    return int(s) if s else 0


def _host_filter_sql(col: str, hosts: list[str]):
    """
    col: jadvaldagi column nomi (masalan: 'link_login' yoki 't.link_login')
    hosts: ['mikrotik.turin.uz', ...]
    """
    clauses, params = [], {}
    for i, h in enumerate(hosts):
        key = f"h{i}"
        clauses.append(f"LOWER({col}) LIKE :{key}")
        params[key] = f"%{h.lower()}%"
    if not clauses:
        # fallback: nom bo‘yicha (masalan, '%turin%')
        clauses.append(f"LOWER({col}) LIKE :fallback")
        params["fallback"] = "%unknown%"
    return "(" + " OR ".join(clauses) + ")", params


@wifi_bp.route('/api/wifi_data', methods=['GET'])
def get_wifi_data():
    try:
        rows = User.query.with_entities(User.link_login).all()
        logger.info(f"Fetched {len(rows)} link_logins from User model")

        unique_sites = set()
        for (link_login,) in rows:
            site = _extract_site_from_link(link_login)
            if site: 
                unique_sites.add(site)

        logins = sorted(unique_sites)

        return jsonify({"logins": logins}), 200
    except Exception as e:
        logger.exception("get_wifi_data failed")
        return jsonify({"logins": []}), 500
    

@wifi_bp.route('/api/link_login/<string:university_name>/dashboard', methods=['GET'])
def university_dashboard_data(university_name):
    try:
        name = (university_name or "").strip().lower()

        # Universitetga tegishli foydalanuvchilar va ulardan hostlar
        users = _collect_university_users(name)  # id, mac, phone, fio, role, link, host
        hosts = sorted({u["host"] for u in users if u.get("host")})
        # Agar userlardan topilmasa ham, minimal fallback: '.<name>.'
        if not hosts:
            hosts = [f".{name}."]

        # ===== Top cards =====
        # 1) Umumiy ulanishlar: user_authorization.link_login bo‘yicha filtr
        ua_clause, ua_params = _host_filter_sql("link_login", hosts)
        total_connections = db.session.execute(
            text(f"SELECT COUNT(*) FROM user_authorization WHERE {ua_clause}"),
            ua_params
        ).scalar() or 0

        # 2) Kunlik daromad (oxirgi 24 soat, faqat success) — perform_time mavjud bo‘lsa undan, aks holda create_time
        success_cond = "LOWER(TRIM(COALESCE(status,''))) = 'success'"
        time_col = "COALESCE(perform_time, create_time)"
        tx_clause, tx_params = _host_filter_sql("link_login", hosts)

        rows_24h = db.session.execute(text(
            f"""
            SELECT amount FROM `transaction`
            WHERE {time_col} >= DATE_SUB(NOW(), INTERVAL 1 DAY)
              AND {success_cond}
              AND {tx_clause}
            """
        ), tx_params).fetchall()
        daily_income = sum(_parse_amount(a) for (a,) in rows_24h)

        # 3) Oylik daromad (oxirgi 30 kun, faqat success)
        rows_30d = db.session.execute(text(
            f"""
            SELECT amount FROM `transaction`
            WHERE {time_col} >= DATE_SUB(NOW(), INTERVAL 30 DAY)
              AND {success_cond}
              AND {tx_clause}
            """
        ), tx_params).fetchall()
        monthly_income = sum(_parse_amount(a) for (a,) in rows_30d)

        # ===== Ulanishlar: Yil/Oy/Kun (faqat shu universitet) =====
        today = date.today()
        uz_mon = ['Yan','Fev','Mar','Apr','May','Iyn','Iyl','Avg','Sen','Okt','Noy','Dek']

        # Day (7 kun)
        day_rows = db.session.execute(text(
            f"""
            SELECT DATE(authorization_date) AS d, COUNT(*) AS cnt
            FROM user_authorization
            WHERE authorization_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
              AND {ua_clause}
            GROUP BY d ORDER BY d
            """
        ), ua_params).fetchall()
        day_map = {d.strftime("%Y-%m-%d"): int(cnt) for d, cnt in day_rows}
        last7 = [today - timedelta(days=i) for i in range(6, -1, -1)]
        day_labels = [str(d.day) for d in last7]
        day_keys   = [d.strftime("%Y-%m-%d") for d in last7]
        day_data   = [day_map.get(k, 0) for k in day_keys]

        # Month (joriy yil 12 oy)
        mon_rows = db.session.execute(text(
            f"""
            SELECT MONTH(authorization_date) AS m, COUNT(*) AS cnt
            FROM user_authorization
            WHERE YEAR(authorization_date) = YEAR(CURDATE())
              AND {ua_clause}
            GROUP BY m ORDER BY m
            """
        ), ua_params).fetchall()
        mon_map = {int(m): int(cnt) for m, cnt in mon_rows}
        mon_labels = uz_mon
        mon_data = [mon_map.get(i+1, 0) for i in range(12)]

        # Year (oxirgi 5 yil)
        yr_rows = db.session.execute(text(
            f"""
            SELECT YEAR(authorization_date) AS y, COUNT(*) AS cnt
            FROM user_authorization
            WHERE authorization_date >= DATE_SUB(CURDATE(), INTERVAL 4 YEAR)
              AND {ua_clause}
            GROUP BY y ORDER BY y
            """
        ), ua_params).fetchall()
        this_year = today.year
        year_labels = [str(this_year - 4 + i) for i in range(5)]
        yr_map = {str(int(y)): int(cnt) for y, cnt in yr_rows}
        year_data = [yr_map.get(lbl, 0) for lbl in year_labels]

        connections_series = {
            "day":   {"labels": day_labels,  "data": day_data},
            "month": {"labels": mon_labels,  "data": mon_data},
            "year":  {"labels": year_labels, "data": year_data},
        }

        # ===== Tushum dinamikasi (faqat shu universitet, faqat success) =====
        # Bar chart stacked (1 dataset: universitet)
        uni_label = name.capitalize()

        # Day (7 kun)
        tx_day = db.session.execute(text(
            f"""
            SELECT amount, DATE({time_col}) AS d
            FROM `transaction`
            WHERE {time_col} >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
              AND {success_cond}
              AND {tx_clause}
            """
        ), tx_params).fetchall()
        day_amount_map = {k: 0 for k in day_keys}
        for amt, d in tx_day:
            key = d.strftime("%Y-%m-%d")
            if key in day_amount_map:
                day_amount_map[key] += _parse_amount(amt)
        uni_day_series = [day_amount_map[k] for k in day_keys]

        # Month (joriy yil 12 oy)
        tx_mon = db.session.execute(text(
            f"""
            SELECT amount, MONTH({time_col}) AS m
            FROM `transaction`
            WHERE YEAR({time_col}) = YEAR(CURDATE())
              AND {success_cond}
              AND {tx_clause}
            """
        ), tx_params).fetchall()
        mon_amounts = [0]*12
        for amt, m in tx_mon:
            idx = int(m) - 1
            if 0 <= idx < 12:
                mon_amounts[idx] += _parse_amount(amt)

        # Year (oxirgi 5 yil)
        tx_yr = db.session.execute(text(
            f"""
            SELECT amount, YEAR({time_col}) AS y
            FROM `transaction`
            WHERE {time_col} >= DATE_SUB(CURDATE(), INTERVAL 4 YEAR)
              AND {success_cond}
              AND {tx_clause}
            """
        ), tx_params).fetchall()
        year_index = {int(y): i for i, y in enumerate(range(this_year-4, this_year+1))}
        yr_amounts = [0]*5
        for amt, y in tx_yr:
            y = int(y)
            if y in year_index:
                yr_amounts[year_index[y]] += _parse_amount(amt)

        income_dynamic = {
            "day":   {"labels": day_labels,  "series": {uni_label: uni_day_series}},
            "month": {"labels": mon_labels,  "series": {uni_label: mon_amounts}},
            "year":  {"labels": year_labels, "series": {uni_label: yr_amounts}},
        }

        # ===== Yangi foydalanuvchilar (shu universitet) =====
        uni_ids = [u["id"] for u in users]
        new_accounts_data = []
        if uni_ids:
            last_users = (
                db.session.query(User)
                .filter(User.id.in_(uni_ids))
                .order_by(User.id.desc())
                .limit(5).all()
            )
            for u in last_users:
                last_auth = (u.authorizations[-1].authorization_date if u.authorizations else "")
                new_accounts_data.append({
                    "id": u.id,
                    "date": str(last_auth),
                    "user": u.fio,
                    "account": "Verified" if not u.block else "Blocked",
                    "username": u.phone_number
                })

        # ===== So‘nggi tranzaksiyalar (shu universitet) =====
        recent_transactions_data = []
        recents = db.session.execute(text(
            f"""
            SELECT id, {time_col} AS t, amount, status, reason
            FROM `transaction`
            WHERE {tx_clause}
            ORDER BY id DESC
            LIMIT 5
            """
        ), tx_params).fetchall()
        for rid, t, amount, status, reason in recents:
            recent_transactions_data.append({
                "id": rid,
                "date": str(t),
                "amount": _parse_amount(amount),
                "status": status,
                "desc": reason
            })

        return jsonify({
            "total_connections": int(total_connections),
            "daily_income": int(daily_income),
            "monthly_income": int(monthly_income),
            "connections_series": connections_series,
            "income_dynamic": income_dynamic,
            "new_accounts": new_accounts_data,
            "recent_transactions": recent_transactions_data
        }), 200

    except Exception as e:
        logger.exception("university_dashboard_data failed")
        return jsonify({"error": "internal"}), 500


@wifi_bp.route('/api/link_login/<string:university_name>/users', methods=['GET'])
def university_users_data(university_name):
    """Paginated + sort + search — faqat ushbu universitet userlari"""
    try:
        # query params
        page  = max(int(request.args.get('page', 1)), 1)
        limit = min(max(int(request.args.get('limit', 20)), 1), 200)
        sort  = (request.args.get('sort') or 'id').lower()
        order = (request.args.get('order') or 'desc').lower()
        q     = (request.args.get('q') or '').strip()

        users = _collect_university_users(university_name)
        # search (clientdan umumiy q)
        if q:
            ql = q.lower()
            users = [
                u for u in users
                if (u["mac"] and ql in u["mac"].lower())
                or (u["fio"] and ql in u["fio"].lower())
                or (u["phone"] and ql in u["phone"].lower())
                or (u["role"] and ql in u["role"].lower())
            ]

        # last authorization date qo‘shamiz (tezkor yo‘l — bitta so‘rov bilan mac set bo‘yicha max date)
        macs = [u["mac"] for u in users if u["mac"]]
        last_auth_map = {}
        if macs:
            sub = db.session.query(
                UserAuthorization.user_mac,
                func.max(UserAuthorization.authorization_date)
            ).filter(
                UserAuthorization.user_mac.in_(macs)
            ).group_by(UserAuthorization.user_mac).all()
            last_auth_map = {m: d for m, d in sub}

        # enrich
        for u in users:
            u["last_authorization"] = str(last_auth_map.get(u["mac"], "") or "")

        # sorting
        keymap = {
            "id": lambda x: x["id"],
            "mac": lambda x: (x["mac"] or ""),
            "fio": lambda x: (x["fio"] or ""),
            "phone": lambda x: (x["phone"] or ""),
            "role": lambda x: (x["role"] or ""),
            "last_authorization": lambda x: (x["last_authorization"] or ""),
        }
        keyfunc = keymap.get(sort, keymap["id"])
        users.sort(key=keyfunc, reverse=(order == 'desc'))

        total = len(users)
        start = (page - 1) * limit
        end   = start + limit
        items = users[start:end]

        # normalize for table
        rows = [{
            "id": u["id"],
            "mac": u["mac"],
            "fio": u["fio"],
            "phone_number": u["phone"],
            "role": u["role"],
            "last_authorization": u["last_authorization"]
        } for u in items]

        return jsonify({
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
            "items": rows
        }), 200
    except Exception:
        logger.exception("university_users_data failed")
        return jsonify({"total": 0, "page": 1, "limit": 20, "pages": 0, "items": []}), 500


@wifi_bp.route('/api/link_login/<string:university_name>/transactions', methods=['GET'])
def university_transactions_data(university_name):
    """Paginated + sort + search — Transaction.link_login URL ichida universitet nomiga qarab"""
    try:
        page  = max(int(request.args.get('page', 1)), 1)
        limit = min(max(int(request.args.get('limit', 20)), 1), 200)
        sort  = (request.args.get('sort') or 'id').lower()
        order = (request.args.get('order') or 'desc').lower()
        q     = (request.args.get('q') or '').strip()

        qry = db.session.query(Transaction).filter(
            Transaction.link_login.ilike(f"%{university_name}%")
        )

        if q:
            like = f"%{q}%"
            qry = qry.filter(
                (Transaction.phone_number.ilike(like)) |
                (Transaction.amount.cast(db.String).ilike(like)) |
                (Transaction.status.ilike(like)) |
                (Transaction.reason.ilike(like)) |
                (Transaction.transaction_id.ilike(like)) |
                (Transaction.id.cast(db.String).ilike(like))
            )

        sortmap = {
            "id": Transaction.id,
            "date": Transaction.create_time,
            "amount": Transaction.amount,
            "status": Transaction.status,
            "phone": Transaction.phone_number
        }
        col = sortmap.get(sort, Transaction.id)
        qry = qry.order_by(desc(col) if order == 'desc' else asc(col))

        total = qry.count()
        items = qry.offset((page - 1) * limit).limit(limit).all()

        rows = [{
            "id": t.id,
            "date": t.create_time.strftime("%Y-%m-%d %H:%M:%S") if t.create_time else "",
            "amount": t.amount,
            "status": t.status,
            "desc": t.reason,
            "phone_number": t.phone_number,
            "transaction_id": t.transaction_id,
            "link_login": t.link_login
        } for t in items]

        return jsonify({
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
            "items": rows
        }), 200

    except Exception:
        logger.exception("university_transactions_data failed")
        return jsonify({"total": 0, "page": 1, "limit": 20, "pages": 0, "items": []}), 500
