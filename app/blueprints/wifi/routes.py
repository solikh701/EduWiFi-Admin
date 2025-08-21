from . import wifi_bp
from ...extensions import db
from urllib.parse import urlparse
from flask import jsonify, request
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
        users = _collect_university_users(university_name)
        macs   = [u["mac"] for u in users if u["mac"]]
        phones = [u["phone"] for u in users if u["phone"]]
        hosts  = [u["host"] for u in users if u["host"]]

        # 1) Umumiy ulanishlar (shu universitet userlari)
        total_connections = 0
        if macs:
            total_connections = (
                db.session.query(func.count(UserAuthorization.id))
                .filter(UserAuthorization.user_mac.in_(macs))
                .scalar()
            ) or 0

        # 2) Umumiy WiFi lar soni — host bo‘yicha unikal
        total_wifi = len(set(hosts))

        # 3) Oylik daromad — oxirgi 30 kun ichidagi shu universitet foydalanuvchilari tranzaksiyalari
        monthly_income = 0
        if phones:
            monthly_income = db.session.execute(text("""
                SELECT COALESCE(SUM(amount),0) FROM `transaction`
                WHERE phone_number IN :phones
                AND create_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """), {"phones": tuple(phones) if len(phones) > 1 else tuple(phones) + ('',)}
            ).scalar() or 0

        # 4) Ulanishlar grafigi (oylar bo‘yicha)
        connections_chart = []
        if macs:
            rows = db.session.query(
                func.year(UserAuthorization.authorization_date).label('y'),
                func.month(UserAuthorization.authorization_date).label('m'),
                func.count(UserAuthorization.id)
            ).filter(
                UserAuthorization.user_mac.in_(macs)
            ).group_by('y', 'm').order_by('y', 'm').all()
            # faqat count larni qaytaramiz
            connections_chart = [r[2] for r in rows]

        # 5) WiFi bo‘yicha tushum (host => sum)
        wifi_income_data = []
        if phones and hosts:
            # telefon raqami bo‘yicha jami tushum (hostni userdan olamiz)
            income_by_host = {}
            for h in set(hosts):
                income_by_host[h] = 0

            # Har bir user telefoni bo‘yicha sum olib, uning hostiga qo‘shamiz
            for u in users:
                pn = u["phone"]
                h  = u["host"]
                if not pn or not h:
                    continue
                amt = db.session.execute(text("""
                    SELECT COALESCE(SUM(amount),0) FROM `transaction` WHERE phone_number=:pn
                """), {"pn": pn}).scalar() or 0
                income_by_host[h] += amt

            wifi_income_data = [{"name": host, "value": val} for host, val in income_by_host.items()]

        # 6) So‘nggi 5 ta foydalanuvchi (shu universitet userlari)
        #    id bo‘yicha eng oxirgilari
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

        # 7) So‘nggi 5 tranzaksiya (shu universitet foydalanuvchilari)
        recent_transactions_data = []
        if phones:
            recents = (
                db.session.query(Transaction)
                .filter(Transaction.phone_number.in_(phones))
                .order_by(Transaction.id.desc())
                .limit(5).all()
            )
            for t in recents:
                recent_transactions_data.append({
                    "id": t.id,
                    "date": str(t.create_time),
                    "amount": t.amount,
                    "status": t.status,
                    "desc": t.reason
                })

        return jsonify({
            "total_connections": total_connections,
            "total_wifi": total_wifi,
            "monthly_income": monthly_income,
            "connections_chart": connections_chart,
            "wifi_income_data": wifi_income_data,
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
    """Paginated + sort + search — faqat ushbu universitet userlari tranzaksiyalari"""
    try:
        page  = max(int(request.args.get('page', 1)), 1)
        limit = min(max(int(request.args.get('limit', 20)), 1), 200)
        sort  = (request.args.get('sort') or 'id').lower()
        order = (request.args.get('order') or 'desc').lower()
        q     = (request.args.get('q') or '').strip()

        users = _collect_university_users(university_name)
        phones = [u["phone"] for u in users if u["phone"]]
        if not phones:
            return jsonify({"total": 0, "page": page, "limit": limit, "pages": 0, "items": []}), 200

        qry = db.session.query(Transaction).filter(Transaction.phone_number.in_(phones))

        # search: id/amount/status/desc/phone
        if q:
            like = f"%{q}%"
            qry = qry.filter(
                (Transaction.phone_number.ilike(like)) |
                (Transaction.amount.ilike(like)) |
                (Transaction.status.ilike(like)) |
                (Transaction.reason.ilike(like)) |
                (Transaction.transaction_id.ilike(like))
            )

        # sort mapping
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
            "date": str(t.create_time),
            "amount": t.amount,
            "status": t.status,
            "desc": t.reason,
            "phone_number": t.phone_number,
            "transaction_id": t.transaction_id
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