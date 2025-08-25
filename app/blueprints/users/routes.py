import math
import MySQLdb
from . import users_bp
from sqlalchemy import or_
from ...config import Config
from ...extensions import db
from MySQLdb.cursors import DictCursor
from routeros_api import RouterOsApiPool
from datetime import datetime, timedelta
# from ...redis_utils import remove_user_tariff
from ...logging_config import configure_logging
from flask import request, jsonify, current_app
from ...models import User, UserAuthorization, tariff_plan
from routeros_api.exceptions import RouterOsApiConnectionError
from ...functions import radius_auth, deactivate_latest_authorization_for_mac

logger = configure_logging()


@users_bp.route('/api/users', methods=['GET'])
def get_users():
    try:
        # pagination
        page  = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        # sorting
        sort_by  = (request.args.get('sort_by')  or 'id').lower()
        sort_dir = (request.args.get('sort_dir') or 'asc').lower()
        reverse  = (sort_dir == 'desc')

        def parse_tariff_limit(limit_str):
            if not limit_str:
                return timedelta(0)
            parts = str(limit_str).strip().split()
            if len(parts) != 2:
                return timedelta(0)
            number, unit = parts
            try:
                number = int(number)
            except Exception:
                return timedelta(0)
            if unit in ['minutes', 'minute']:
                return timedelta(minutes=number)
            if unit in ['days', 'day']:
                return timedelta(days=number)
            if unit in ['weeks', 'week']:
                return timedelta(weeks=number)
            if unit in ['months', 'month']:
                return timedelta(days=30 * number)
            return timedelta(0)

        def admin_or_portal(val):
            try:
                return "Admin" if val is not None and str(val).strip().isdigit() else "Portal"
            except Exception:
                return "Portal"

        def dt_from_str(s):
            try:
                return datetime.strptime(s, "%d-%m-%Y %H:%M:%S")
            except Exception:
                return None

        def status_rank(s):
            return 2 if s == 'AKTIV' else (1 if s == 'NOAKTIV' else 0)

        # NOTE: saralash to'g'ri bo‘lishi uchun barcha userlarni olib, so‘ng ro‘yxatga yig‘amiz
        users = User.query.all()
        rows = []
        for u in users:
            last_auth = None
            last_act  = None
            last_tf   = None
            last_tariff_limit = None

            if u.authorizations:
                sorted_auths = sorted(u.authorizations, key=lambda a: a.authorization_date, reverse=True)
                for a in sorted_auths:
                    act = a.authorization_activeness
                    if act not in ['NOINTERNET', 'NOINTERNETPAY']:
                        last_auth = a.authorization_date
                        last_act  = act
                        last_tf   = a.selected_tariff
                        last_tariff_limit = a.tariff_limit
                        break
                if not last_auth:
                    a = sorted_auths[0]
                    last_auth = a.authorization_date
                    last_act  = a.authorization_activeness
                    last_tf   = a.selected_tariff
                    last_tariff_limit = a.tariff_limit

            last_limit_dt = None
            if last_tf and last_tf not in ['Teacher', 'Student', 'Guest']:
                tariff_id = last_tf.replace('tariff', '')
                tariff = tariff_plan.query.get(int(tariff_id)) if tariff_id.isdigit() else None
                if tariff and last_auth:
                    limit_duration = parse_tariff_limit(tariff.duration_days or '')
                    if isinstance(last_auth, str):
                        try:
                            last_auth = datetime.strptime(last_auth, "%d-%m-%Y %H:%M:%S")
                        except ValueError:
                            last_auth = None
                    if isinstance(last_auth, datetime):
                        last_limit_dt = last_auth + limit_duration
            elif last_auth and last_tf in ['Teacher', 'Student', 'Guest']:
                try:
                    minutes = int(last_tariff_limit) if last_tariff_limit else 0
                    last_limit_dt = last_auth + timedelta(minutes=minutes)
                except Exception:
                    last_limit_dt = None

            item = {
                'id': u.id,
                'MAC': u.MAC,
                'fio': u.fio,
                'phone_number': u.phone_number,
                'last_authorization': last_auth.strftime("%d-%m-%Y %H:%M:%S") if isinstance(last_auth, datetime) else None,
                'last_authorization_limit': last_limit_dt.strftime("%d-%m-%Y %H:%M:%S") if isinstance(last_limit_dt, datetime) else None,
                'authorization_activeness': last_act,
                'role': u.role,
                'last_tariff_limit': last_tariff_limit,
                'activated_by': admin_or_portal(last_tariff_limit),
            }
            rows.append(item)

        # sorting
        def key_func(r):
            if   sort_by == 'id':   return r['id']
            elif sort_by == 'mac':  return (r['MAC'] or '').lower()
            elif sort_by == 'fio':  return (r['fio'] or '').lower()
            elif sort_by == 'phone' or sort_by == 'phone_number':
                return (r['phone_number'] or '').lower()
            elif sort_by == 'role': return (r['role'] or '').lower()
            elif sort_by == 'last_authorization':
                dt = dt_from_str(r['last_authorization']);  return dt or datetime.min
            elif sort_by == 'last_authorization_limit':
                dt = dt_from_str(r['last_authorization_limit']);  return dt or datetime.min
            elif sort_by == 'authorization_activeness':
                return status_rank(r['authorization_activeness'])
            elif sort_by == 'activated_by':
                return 1 if r.get('activated_by') == 'Admin' else 0
            else:
                return r['id']

        rows.sort(key=key_func, reverse=reverse)

        total = len(rows)
        start = (page - 1) * limit
        end   = start + limit
        page_rows = rows[start:end]

        return jsonify({'users': page_rows, 'total': total}), 200

    except Exception as e:
        logger.error(f"Error in get_users: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@users_bp.route('/api/users/search', methods=['GET'])
def search_users():
    try:
        # 1. Qidiruv so‘rovi qabul qilindi va log qilindi
        search_term = request.args.get('search', default='', type=str).strip().lower()
        logger.info(f"[search_users] Kiritilgan search parameter: '{search_term}'")
        pattern = f"%{search_term}%"

        # 2. Agar search bo‘sh bo‘lsa, barcha foydalanuvchilar o‘qiladi
        if not search_term:
            users = User.query.all()
            logger.info(f"[search_users] Bo‘sh qidiruv – barcha foydalanuvchilar o‘qildi (soni={len(users)})")
        else:
            users = User.query.filter(
                or_(
                    User.MAC.ilike(pattern),
                    User.fio.ilike(pattern),
                    User.phone_number.ilike(pattern),
                    User.role.ilike(pattern)
                )
            ).all()
            logger.info(f"[search_users] Filtrlash natijasi – topilgan foydalanuvchilar soni={len(users)}")

        def parse_tariff_limit(limit_str):
            if not limit_str:
                return timedelta(0)
            parts = limit_str.strip().split()
            if len(parts) != 2:
                return timedelta(0)
            num, unit = parts
            num = int(num)
            if unit.startswith('minute'):
                return timedelta(minutes=num)
            if unit.startswith('day'):
                return timedelta(days=num)
            if unit.startswith('week'):
                return timedelta(weeks=num)
            if unit.startswith('month'):
                return timedelta(days=30 * num)
            return timedelta(0)

        def get_activation_source(val):
            try:
                if val is not None and str(val).strip().isdigit():
                    return "Admin"
            except Exception:
                pass
            return "Portal"

        result = []
        now = datetime.now()

        # 3. Har bir topilgan user uchun kerakli maydonlar tayyorlanadi va log qilinadi
        for u in users:
            if u.authorizations:
                latest_auth = max(u.authorizations, key=lambda a: a.authorization_date)
                last_auth = latest_auth.authorization_date
                last_act = latest_auth.authorization_activeness
                last_tf = latest_auth.selected_tariff
                last_tariff_limit = latest_auth.tariff_limit

                logger.debug(
                    f"[search_users] User ID={u.id} – Oxirgi authorization: "
                    f"date={last_auth}, activeness={last_act}, "
                    f"tariff={last_tf}, limit={last_tariff_limit}"
                )
            else:
                last_auth = None
                last_act = None
                last_tf = None
                last_tariff_limit = None
                logger.debug(f"[search_users] User ID={u.id} da authorization yozuvi yo‘q")

            last_limit_dt = None
            if last_tf and last_tf not in ['Teacher', 'Student', 'Guest']:
                tariff_id = last_tf.replace('tariff', '')
                tariff = tariff_plan.query.get(int(tariff_id)) if tariff_id.isdigit() else None
                if tariff and last_auth:
                    limit_duration = parse_tariff_limit(tariff.duration_days or '')
                    if isinstance(last_auth, str):
                        try:
                            last_auth = datetime.strptime(last_auth, "%d-%m-%Y %H:%M:%S")
                        except ValueError:
                            last_auth = None
                    if isinstance(last_auth, datetime):
                        last_limit_dt = last_auth + limit_duration
            elif last_auth and last_tf in ['Teacher', 'Student', 'Guest']:
                try:
                    minutes = int(last_tariff_limit) if last_tariff_limit else 0
                    limit_duration = timedelta(minutes=minutes)
                    last_limit_dt = last_auth + limit_duration
                except Exception:
                    last_limit_dt = None

            result.append({
                'id': u.id,
                'MAC': u.MAC,
                'fio': u.fio,
                'phone_number': u.phone_number,
                'SSID': None,
                'last_authorization': (
                    last_auth.strftime("%d-%m-%Y %H:%M:%S") if isinstance(last_auth, datetime) else None
                ),
                'last_authorization_limit': (
                    last_limit_dt.strftime("%d-%m-%Y %H:%M:%S") if isinstance(last_limit_dt, datetime) else None
                ),
                'authorization_activeness': last_act,
                'role': u.role,
                'last_tariff_limit': last_tariff_limit,
                'activated_by': get_activation_source(last_tariff_limit),
            })

        # 4. Natija JSON shaklida va log qilinib qaytariladi
        logger.info(f"[search_users] So‘rov natijasi tayyor, jami {len(result)} ta user qaytarilmoqda")
        return jsonify({
            "users": result,
            "total": len(result)
        }), 200

    except Exception as e:
        logger.error(f"[search_users] Xatolik yuz berdi: {e}")
        return jsonify({"error": "Search failed"}), 500


@users_bp.route('/api/users/<int:user_id>', methods=['GET'])
def get_user_details(user_id):
    try:
        logger.info(f"[get_user_details] Kiritilgan user_id: {user_id}")

        DT_FMT = "%H:%M:%S %d-%m-%Y"
        user = User.query.get(user_id)
        if user is None:
            logger.warning(f"[get_user_details] User topilmadi – ID={user_id}")
            return jsonify({'error': 'User not found'}), 404

        logger.debug(f"[get_user_details] User topildi – ID={user.id}, MAC={user.MAC}, fio={user.fio}")

        authorizations = sorted(user.authorizations, key=lambda x: x.authorization_date)
        earliest_auth = authorizations[0] if authorizations else None
        latest_auth   = authorizations[-1] if authorizations else None

        if earliest_auth:
            earliest_date = earliest_auth.authorization_date
            earliest_tariff = earliest_auth.selected_tariff
            earliest_limit = earliest_auth.tariff_limit
            logger.debug(
                f"[get_user_details] Eng birinchi authorization: date={earliest_date}, "
                f"tariff={earliest_tariff}, limit={earliest_limit}"
            )
        else:
            earliest_date = None
            earliest_tariff = None
            earliest_limit = None
            logger.debug("[get_user_details] User da birorta ham authorization yozuvi yo‘q")

        if latest_auth:
            latest_date = latest_auth.authorization_date
            latest_act = latest_auth.authorization_activeness
            latest_tariff = latest_auth.selected_tariff
            latest_limit = latest_auth.tariff_limit
            logger.debug(
                f"[get_user_details] Eng so‘ngi authorization: date={latest_date}, "
                f"activeness={latest_act}, tariff={latest_tariff}, limit={latest_limit}"
            )
        else:
            latest_date = None
            latest_act = None
            latest_tariff = None
            latest_limit = None

        # 1. Qolgan vaqtni hisoblash
        remaining_str = None
        if latest_date and latest_limit:
            try:
                if latest_tariff in ['Teacher', 'Student', 'Guest']:
                    td = timedelta(minutes=int(user.last_tariff_limit))
                else:
                    parts = str(latest_limit).strip().split()
                    if len(parts) == 2:
                        num, unit = parts
                        num = int(num)
                        if unit.startswith('minute'):
                            td = timedelta(minutes=num)
                        elif unit.startswith('day'):
                            td = timedelta(days=num)
                        elif unit.startswith('week'):
                            td = timedelta(weeks=num)
                        elif unit.startswith('month'):
                            td = timedelta(days=30 * num)
                        else:
                            td = timedelta(0)
                    else:
                        td = timedelta(0)
                remaining_time = max(timedelta(0), (latest_date + td) - datetime.now())
                total_seconds = int(remaining_time.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                remaining_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                logger.debug(f"[get_user_details] Foydalanuvchining qolgan vaqti: {remaining_str}")
            except Exception as ex:
                remaining_str = None
                logger.error(f"[get_user_details] Qolgan vaqtni hisoblashda xato: {ex}")
        else:
            logger.debug("[get_user_details] Qolgan vaqtni hisoblashi uchun ma’lumot yetarli emas")

        # 2. So‘ngi IP-manzil va umumiy sessiyalar soni olish
        last_ip = None
        session_cnt = 0
        try:
            conn = MySQLdb.connect(
                host=Config.DB_HOST, user=Config.DB_USER, passwd=Config.DB_PASS_RAW,
                db=Config.DB_NAME, charset='utf8', cursorclass=DictCursor
            )
            cursor = conn.cursor()
            cursor.execute("""
                SELECT framedipaddress FROM radacct
                WHERE username = %s
                ORDER BY acctstarttime DESC
                LIMIT 1
            """, (user.MAC,))
            row = cursor.fetchone()
            last_ip = row['framedipaddress'] if row else None

            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM radacct
                WHERE username = %s
            """, (user.MAC,))
            session_cnt = cursor.fetchone()['cnt'] if cursor else 0
            cursor.close()
            conn.close()
            logger.debug(f"[get_user_details] So‘ngi IP: {last_ip}, sessiyalar soni: {session_cnt}")
        except Exception as ex:
            logger.error(f"[get_user_details] RADIUS ma’lumotlarini olishda xato: {ex}")

        # 3. Tariff nomini o‘zgartirish
        if latest_tariff == 'tariff1':
            latest_tariff_str = '1-Tarif'
        elif latest_tariff == 'tariff2':
            latest_tariff_str = '2-Tarif'
        elif latest_tariff == 'tariff3':
            latest_tariff_str = '3-Tarif'
        elif latest_tariff == 'tariff4':
            latest_tariff_str = '4-Tarif'
        elif latest_tariff in ['Student', 'Teacher', 'Guest']:
            latest_tariff_str = f"{user.last_tariff_limit}-minut"
        else:
            latest_tariff_str = latest_tariff

        # 4. Natija tayyorlanadi
        result = {
            'id': user.id,
            'MAC': user.MAC,
            'fio': user.fio,
            'phone_number': user.phone_number,
            'confirmation_code': user.confirmation_code,
            'role': user.role,
            'overall_authorizations': user.overall_authorizations,
            'overall_payed_sum': user.overall_payed_sum,
            'block': user.block,
            'first_authorization': earliest_date.strftime(DT_FMT) if earliest_date else None,
            'last_authorization': latest_date.strftime(DT_FMT) if latest_date else None,
            'authorization_activeness': latest_act,
            'selectedTariff': latest_tariff_str,
            'tariff_limit': latest_limit,
            'remaining_time': (
                remaining_str if latest_act == 'AKTIV' and remaining_str is not None else '00:00:00'
            ),
            'last_ip_address': last_ip,
            'total_sessions': session_cnt
        }

        logger.info(f"[get_user_details] Foydalanuvchi ma’lumotlari tayyor, ID={user.id}")
        logger.debug(f"[get_user_details] Qaytarilayotgan JSON: {result}")

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"[get_user_details] Xatolik yuz berdi: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@users_bp.route('/api/updateMacAddress', methods=['POST'])
def update_mac_address():
    data = request.json
    phone_number = data.get('phone_number')
    old_mac = data.get('oldMAC')
    new_mac = data.get('newMAC')
    logger.info(f"[updateMacAddress] Received request: phone_number={phone_number}, oldMAC={old_mac}, newMAC={new_mac}")

    if not phone_number or not new_mac or not old_mac:
        logger.error("[updateMacAddress] Missing data in request")
        return jsonify({'success': False, 'error': 'Missing data'}), 400

    user = User.query.filter_by(MAC=old_mac).first()
    if not user:
        logger.error(f"[updateMacAddress] User not found for oldMAC={old_mac}")
        return jsonify({'success': False, 'error': 'User not found'}), 404

    user.MAC = new_mac
    db.session.commit()
    logger.info(f"[updateMacAddress] Updated MAC from {old_mac} to {new_mac} for phone_number={phone_number}")

    # WebSocket: notify open tables
    try:
        current_app.emit_refresh('users')
        current_app.emit_refresh(f'user_sessions:{user.id}')
    except Exception as e:
        logger.warning(f"[updateMacAddress] emit_refresh failed: {e}")

    return jsonify({'success': True}), 200


@users_bp.route('/api/updateStatus', methods=['POST'])
def update_status():
    data = request.get_json()
    new_status = data.get('status')
    phone_number = data.get('phone_number')
    logger.info(f"[updateStatus] Received request: phone_number={phone_number}, status={new_status}")

    if not phone_number or new_status is None:
        logger.error("[updateStatus] Invalid data in request")
        return jsonify({'error': 'Invalid data'}), 400

    status_flag = 1 if new_status == 'Bloklangan' else 0
    logger.debug(f"[updateStatus] Mapped status '{new_status}' to flag {status_flag}")

    user = User.query.filter_by(phone_number=phone_number).first()
    if user:
        user.block = status_flag
        db.session.commit()
        logger.info(f"[updateStatus] Updated block={status_flag} for phone_number={phone_number}")

        # WebSocket: notify
        try:
            current_app.emit_refresh('users')
            current_app.emit_refresh(f'user_sessions:{user.id}')
        except Exception as e:
            logger.warning(f"[updateStatus] emit_refresh failed: {e}")

        return jsonify({'message': 'Status updated successfully'}), 200
    else:
        logger.error(f"[updateStatus] User not found for phone_number={phone_number}")
        return jsonify({'error': 'User not found'}), 404
    

@users_bp.route('/api/unauthorization', methods=['POST'])
def unauthorize_user():
    data = request.get_json()
    user_id      = data.get('id')
    phone_number = data.get('phone_number')
    mac          = data.get('MAC') or data.get('macAddress')
    logger.info(f"[unauthorization] Received request: id={user_id}, phone_number={phone_number}, MAC={mac}")

    # 1) Foydalanuvchini topamiz
    user = None
    if user_id:
        user = User.query.get(user_id)
        logger.debug(f"[unauthorization] Queried User by id={user_id}: {user}")
    elif mac:
        user = User.query.filter_by(MAC=mac).first()
        logger.debug(f"[unauthorization] Queried User by MAC={mac}: {user}")
    else:
        logger.error("[unauthorization] Missing user identifier")
        return jsonify({'success': False, 'error': 'Missing user identifier'}), 400

    if not user:
        logger.error("[unauthorization] User not found")
        return jsonify({'success': False, 'error': 'User not found'}), 404

    username = user.MAC  # sizda username ham password MAC bo'lib ishlatilayotgan ko‘rinadi
    logger.info(f"[unauthorization] Deauthorizing user with MAC/username={username}")

    # 2) RADIUS tozalash (radgroupreply, radusergroup)
    conn = None
    cur  = None
    try:
        conn = MySQLdb.connect(
            host=Config.DB_HOST, user=Config.DB_USER, passwd=Config.DB_PASS_RAW, db=Config.DB_NAME,
            charset='utf8', cursorclass=DictCursor
        )
        cur = conn.cursor()

        # radius_auth true qaytsa, tarif bog'lamalari mavjud deyapmiz
        if radius_auth(username, username):
            cur.execute("DELETE FROM radgroupreply WHERE groupname = %s", (f"tariff_{username}",))
            cur.execute("DELETE FROM radusergroup  WHERE username  = %s", (username,))
            logger.info(f"[unauthorization] Removed RADIUS entries for username={username}")

        conn.commit()
    except Exception as e:
        logger.exception(f"[unauthorization] Error cleaning RADIUS: {e}")
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass

    # 3) MikroTik Hotspot sessiyasini o'chirish
    api = None
    try:
        api = RouterOsApiPool(
            Config.MIKROTIK_HOST, username=Config.MIKROTIK_USER,
            password=Config.MIKROTIK_PASSWORD, plaintext_login=True
        )
        api_obj = api.get_api()
        hotspot_active = api_obj.get_resource('/ip/hotspot/active')

        def _remove(mac_addr: str) -> bool:
            try:
                active = hotspot_active.get()
                for u in active:
                    if u.get('user', '').strip().upper() == mac_addr.strip().upper():
                        hotspot_active.remove(id=u['id'])
                        logger.info(f"[unauthorization] Removed active hotspot session id={u['id']} for MAC={mac_addr}")
                        return True
            except Exception as e:
                logger.exception(f"[unauthorization] Error listing/removing active sessions: {e}")
            return False

        removed = _remove(username)
        if not removed:
            try:
                host_res = api_obj.get_resource('/ip/hotspot/host')
                hosts = host_res.get()
                for h in hosts:
                    if h.get('mac-address', '').strip().upper() == username.strip().upper():
                        host_res.remove(id=h['id'])
                        logger.info(f"[unauthorization] Removed hotspot host id={h['id']} for MAC={username}")
                        break
            except Exception as e:
                logger.exception(f"[unauthorization] Error removing host entry: {e}")
    except Exception as e:
        logger.exception(f"[unauthorization] RouterOS cleanup failed: {e}")
    finally:
        if api:
            try:
                api.disconnect()
            except Exception:
                pass
        logger.info("[unauthorization] RouterOS API disconnected (if opened)")

    # 4) Bizning bazadagi oxirgi avtorizatsiyani noaktiv qilish
    try:
        deactivate_latest_authorization_for_mac(user.MAC)
        logger.info(f"[unauthorization] Deactivated latest authorization for MAC={user.MAC}")
    except Exception as e:
        logger.exception(f"[unauthorization] Failed to deactivate latest authorization: {e}")

    # WebSocket: notify open tables
    try:
        current_app.emit_refresh('users')
        current_app.emit_refresh(f'user_sessions:{user.id}')
    except Exception as e:
        logger.warning(f"[unauthorization] emit_refresh failed: {e}")

    return jsonify({'success': True, 'message': 'User unauthorized successfully'}), 200


@users_bp.route('/api/deleteUser', methods=['DELETE'])
def delete_user():
    data        = request.get_json()
    mac_address = data.get('MAC') or data.get('macAddress')
    logger.info(f"[deleteUser] Received request: MAC={mac_address}")

    if not mac_address:
        logger.error("[deleteUser] Missing user identifier")
        return jsonify({'success': False, 'error': 'Missing user identifier'}), 400

    user = User.query.filter_by(MAC=mac_address).first()
    if not user:
        logger.error("[deleteUser] User not found")
        return jsonify({'success': False, 'error': 'User not found'}), 404

    # 1) Avval o'z DB’dan o‘chiramiz
    UserAuthorization.query.filter_by(user_mac=user.MAC).delete()
    db.session.delete(user)
    db.session.commit()
    logger.info(f"[deleteUser] Deleted User and authorizations from DB: MAC={mac_address}")

    # 2) RADIUS tozalash (try/except bilan)
    conn = None
    cur  = None
    try:
        conn = MySQLdb.connect(
            host=Config.DB_HOST, user=Config.DB_USER, passwd=Config.DB_PASS_RAW,
            db=Config.DB_NAME, charset='utf8', cursorclass=DictCursor
        )
        cur = conn.cursor()
        # sizda username/password sifatida MAC ishlatilgan
        username = mac_address
        if radius_auth(username, username):
            cur.execute("DELETE FROM radgroupreply WHERE groupname = %s", (f"tariff_{username}",))
            cur.execute("DELETE FROM radusergroup  WHERE username  = %s", (username,))
            logger.info(f"[deleteUser] Removed RADIUS entries for username={username}")
        conn.commit()
    except Exception as e:
        logger.exception(f"[deleteUser] RADIUS cleanup failed: {e}")
        if conn:
            try: conn.rollback()
            except Exception: pass
    finally:
        if cur:
            try: cur.close()
            except Exception: pass
        if conn:
            try: conn.close()
            except Exception: pass

    # 3) MikroTik Hotspot tozalash – ulana olmasak ham 500 bermaymiz
    api = None
    mikrotik_cleanup_ok = True
    try:
        api = RouterOsApiPool(
            Config.MIKROTIK_HOST,
            username=Config.MIKROTIK_USER,
            password=Config.MIKROTIK_PASSWORD,
            port=getattr(Config, "MIKROTIK_PORT", 8728),
            plaintext_login=True,
            socket_timeout=5,
        )
        api_obj = api.get_api()
        hotspot_active = api_obj.get_resource('/ip/hotspot/active')
        host_res       = api_obj.get_resource('/ip/hotspot/host')

        # active sessiyani MAC useri bo'yicha o'chirish
        try:
            for u in hotspot_active.get():
                if u.get('user', '').strip().upper() == mac_address.strip().upper():
                    hotspot_active.remove(id=u['id'])
                    logger.info(f"[deleteUser] Removed active hotspot session id={u['id']}")
                    break
        except Exception as e:
            logger.exception(f"[deleteUser] Error removing active session: {e}")

        # host ro'yxatidan ham o'chirishga urinamiz
        try:
            for h in host_res.get():
                if h.get('mac-address', '').strip().upper() == mac_address.strip().upper():
                    host_res.remove(id=h['id'])
                    logger.info(f"[deleteUser] Removed hotspot host id={h['id']}")
                    break
        except Exception as e:
            logger.exception(f"[deleteUser] Error removing host entry: {e}")

    except RouterOsApiConnectionError as e:
        mikrotik_cleanup_ok = False
        logger.warning(f"[deleteUser] MikroTik API ga ulanib bo'lmadi (skipping): {e}")
    except Exception as e:
        mikrotik_cleanup_ok = False
        logger.exception(f"[deleteUser] Unexpected MikroTik error: {e}")
    finally:
        if api:
            try: api.disconnect()
            except Exception: pass
        logger.info("[deleteUser] RouterOS API disconnected (if opened)")

    # WebSocket: notify
    try:
        current_app.emit_refresh('users')
        # If the deleted user's session page is open somewhere, refresh it too
        current_app.emit_refresh(f'user_sessions:{user.id}')
    except Exception as e:
        logger.warning(f"[deleteUser] emit_refresh failed: {e}")

    # 4) Javob – MikroTik bo'lmasa ham 200 qaytaramiz
    return jsonify({
        'success': True,
        'message': 'User deleted from DB. MikroTik cleanup {}'.format(
            'done' if mikrotik_cleanup_ok else 'skipped (connection failed)'
        )
    }), 200
    

@users_bp.route('/api/users/<int:user_id>/authorizations', methods=['GET'])
def get_user_authorizations(user_id):
    try:
        logger.info(f"[get_user_authorizations] Request received for user_id={user_id}")
        user = User.query.get(user_id)
        if not user:
            logger.error(f"[get_user_authorizations] User not found: user_id={user_id}")
            return jsonify({"error": "User not found"}), 404

        page     = request.args.get('page',     default=1,   type=int)
        per_page = request.args.get('per_page', default=20,  type=int)
        search   = request.args.get('search',   default="",  type=str).strip().lower()

        # NEW: sort params
        sort_by  = request.args.get('sort_by',  default='date', type=str).lower()
        sort_dir = request.args.get('sort_dir', default='desc', type=str).lower()
        sort_dir = 'desc' if sort_dir not in ('asc', 'desc') else sort_dir
        reverse  = (sort_dir == 'desc')

        def fetch_price(tarif_name):
            if tarif_name and tarif_name.startswith("tariff") and tarif_name[6:].isdigit():
                plan_id = int(tarif_name[6:])
                row = tariff_plan.query.filter_by(id=plan_id).first()
                return row.price if row else "Unknown"
            return "Admin"

        # build list
        authorizations = sorted(user.authorizations, key=lambda x: x.authorization_date, reverse=True)
        all_items = []
        for auth in authorizations:
            raw_status = (getattr(auth, 'authorization_activeness', '') or '').strip().upper()
            status_map = {
                'AKTIV': 'AKTIV',
                'NOAKTIV': 'NOAKTIV',
                'NOINTERNETPAY': 'NOAKTIV',
                'NO INTERNET PAY': 'NOAKTIV',
                'NO_INTERNET_PAY': 'NOAKTIV',
                'BLOCKED': 'NOAKTIV',
                'EXPIRED': 'NOAKTIV',
            }
            status = status_map.get(raw_status, raw_status or 'NOAKTIV')

            date_str = auth.authorization_date.strftime("%d-%m-%Y %H:%M:%S")                        if isinstance(auth.authorization_date, datetime) else str(auth.authorization_date)
            tarif    = auth.selected_tariff
            limit    = auth.tariff_limit
            price    = fetch_price(tarif)
            hostname = getattr(auth, 'ip_address', "") or ""

            if tarif == 'tariff1':
                tarif_display = '1-Tarif'
            elif tarif == 'tariff2':
                tarif_display = '2-Tarif'
            elif tarif == 'tariff3':
                tarif_display = '3-Tarif'
            elif tarif == 'tariff4':
                tarif_display = '4-Tarif'
            elif tarif in ['Student', 'Teacher', 'Guest']:
                tarif_display = (limit or '') + "-minut"
                price = "Admin"
            else:
                tarif_display = tarif or ""

            all_items.append({
                "date":     date_str,
                "hostname": hostname,
                "tarif":    tarif_display,
                "price":    price,
                "status":   status
            })

        # search
        if search:
            def matches(item):
                return (
                    search in item["date"].lower() or
                    search in item["hostname"].lower() or
                    search in item["tarif"].lower() or
                    search in str(item["price"]).lower() or
                    search in str(item["status"]).lower()
                )
            all_items = [i for i in all_items if matches(i)]

        # NEW: sort across all items
        def parse_dt(s):
            try:
                return datetime.strptime(s, "%d-%m-%Y %H:%M:%S")
            except Exception:
                return datetime.min

        def price_val(p):
            try:
                return float(p)
            except Exception:
                # "Admin" yoki "Unknown"
                return -1.0 if str(p).lower() == 'admin' else float('inf')

        def status_rank(s):
            return 2 if s == 'AKTIV' else (1 if s == 'NOAKTIV' else 0)

        if   sort_by == 'date':
            all_items.sort(key=lambda i: parse_dt(i['date']), reverse=reverse)
        elif sort_by == 'hostname':
            all_items.sort(key=lambda i: (i['hostname'] or '').lower(), reverse=reverse)
        elif sort_by == 'tarif':
            all_items.sort(key=lambda i: (i['tarif'] or '').lower(), reverse=reverse)
        elif sort_by == 'price':
            all_items.sort(key=lambda i: price_val(i['price']), reverse=reverse)
        elif sort_by == 'status':
            all_items.sort(key=lambda i: status_rank(i['status']), reverse=reverse)
        else:
            # default fallback
            all_items.sort(key=lambda i: parse_dt(i['date']), reverse=True)

        # paginate
        total       = len(all_items)
        total_pages = max(1, math.ceil(total / per_page))
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end   = start + per_page
        items = all_items[start:end]

        logger.info(f"[get_user_authorizations] Request sended for user_id={user_id}, items={items}")
        return jsonify({
            "page":        page,
            "per_page":    per_page,
            "total":       total,
            "total_pages": total_pages,
            "items":       items
        }), 200

    except Exception as e:
        logger.error(f"[get_user_authorizations] Error: {e}")
        return jsonify({"error": "An error occurred, please check the server logs."}), 500
