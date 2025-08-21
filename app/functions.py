from routeros_api.exceptions import RouterOsApiConnectionError
from app.models import User, db, UserAuthorization
from app.logging_config import configure_logging
from routeros_api import RouterOsApiPool
from pyrad.dictionary import Dictionary
from pyrad.packet import AccessRequest
from MySQLdb.cursors import DictCursor
from pyrad.client import Client
from datetime import timedelta
from app.config import Config
import traceback
import MySQLdb
import sys
import os

logger = configure_logging()


def allowed_file(filename):
    from app import app
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def reorder_user_ids():
    from app import db
    users = User.query.order_by(User.id).all()
    new_id = 1

    for user in users:
        user.id = new_id
        new_id += 1

    db.session.commit()


def save_file_to_directory(request, key, directory):
    if key in request.files:
        file = request.files[key]
        extension = os.path.splitext(file.filename)[1].lower()
        file_name = f"{key}{extension}"
        file_path = os.path.join(directory, file_name)

        for existing_file in os.listdir(directory):
            if existing_file.startswith(key) and existing_file != file_name:
                os.remove(os.path.join(directory, existing_file))

        file.save(file_path)
        return file_path
    return None


def deactivate_latest_authorization_for_mac(mac: str):
    latest = (
        UserAuthorization.query
        .filter_by(user_mac=mac, authorization_activeness='AKTIV')
        .order_by(UserAuthorization.authorization_date.desc())
        .first()
    )
    if not latest:
        print(f"No active authorization to deactivate for MAC={mac}")
        return

    latest.authorization_activeness = 'NOAKTIV'
    db.session.commit()
    print(f"Deactivated id={latest.id} for MAC={mac}")

    db.session.expire_all()


def get_file_url_or_none(file_path, directory):
    if file_path and os.path.exists(file_path):
        file_name = os.path.basename(file_path)
        return f'/ads/{file_name}'
    return None


def radius_auth(username, password):
    srv = Client(server=Config.RADIUS_SERVER, secret=Config.RADIUS_SECRET, dict=Dictionary(Config.RADIUS_DICT_PATHS))
    req = srv.CreateAuthPacket(code=AccessRequest, User_Name=username)
    req["User-Password"] = req.PwCrypt(password)
    try:
        reply = srv.SendPacket(req)
    except Exception as e:
        print("RADIUS connection error:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return False
    return reply.code == 2


def update_tarif_tables(
    tarif_bepul_session_timeout, tarif_bepul_mikrotik_rate_limit, tariff_bepul_mikrotik_total_limit,
    tarif_kun_session_timeout,   tarif_kun_mikrotik_rate_limit,   tariff_kun_mikrotik_total_limit,
    tarif_hafta_session_timeout, tarif_hafta_mikrotik_rate_limit, tariff_hafta_mikrotik_total_limit,
    tarif_oy_session_timeout,    tarif_oy_mikrotik_rate_limit,    tariff_oy_mikrotik_total_limit
):
    connection = None
    cursor = None
    try:
        connection = MySQLdb.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            passwd=Config.DB_PASS_RAW,
            db=Config.DB_NAME,
            charset='utf8',
            cursorclass=DictCursor
        )
        cursor = connection.cursor()

        updates = [
            ('tariff_bepul', 'Session-Timeout', tarif_bepul_session_timeout),
            ('tariff_bepul', 'Mikrotik-Rate-Limit', tarif_bepul_mikrotik_rate_limit),
            ('tariff_bepul', 'Mikrotik-Total-Limit', tariff_bepul_mikrotik_total_limit),

            ('tariff_kun', 'Session-Timeout', tarif_kun_session_timeout),
            ('tariff_kun', 'Mikrotik-Rate-Limit', tarif_kun_mikrotik_rate_limit),
            ('tariff_kun', 'Mikrotik-Total-Limit', tariff_kun_mikrotik_total_limit),

            ('tariff_hafta', 'Session-Timeout', tarif_hafta_session_timeout),
            ('tariff_hafta', 'Mikrotik-Rate-Limit', tarif_hafta_mikrotik_rate_limit),
            ('tariff_hafta', 'Mikrotik-Total-Limit', tariff_hafta_mikrotik_total_limit),

            ('tariff_oy', 'Session-Timeout', tarif_oy_session_timeout),
            ('tariff_oy', 'Mikrotik-Rate-Limit', tarif_oy_mikrotik_rate_limit),
            ('tariff_oy', 'Mikrotik-Total-Limit', tariff_oy_mikrotik_total_limit),
        ]

        for groupname, attribute, value in updates:
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM radgroupreply
                 WHERE groupname = %s AND attribute = %s
            """, (groupname, attribute))
            row = cursor.fetchone()
            if row and row['cnt'] > 0:
                cursor.execute("""
                    UPDATE radgroupreply
                       SET value = %s
                     WHERE groupname = %s AND attribute = %s
                """, (value, groupname, attribute))
            else:
                cursor.execute("""
                    INSERT INTO radgroupreply (groupname, attribute, value)
                    VALUES (%s, %s, %s)
                """, (groupname, attribute, value))

        connection.commit()

    except Exception as e:
        print(f"Error updating tariff tables: {e}", file=sys.stderr)

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_radius_plans():
    try:
        connection = MySQLdb.connect(
            host=Config.DB_HOST,
            user=Config.DB_USER,
            passwd=Config.DB_PASS_RAW,
            db=Config.DB_NAME,
            charset='utf8',
            cursorclass=DictCursor
        )
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM radgroupreply WHERE groupname LIKE 'tariff_%'")

        tarif_plans = cursor.fetchall()

        return tarif_plans
    except Exception as e:
        print(f"Error: {e}")
        return None
    

def get_latest_authorization(user):
    if not user.authorizations:
        return None, None, None

    latest_auth = max(user.authorizations, key=lambda a: a.authorization_date)
    return (
        latest_auth.authorization_date,
        latest_auth.authorization_activeness,
        latest_auth.tariff_limit
    )

def deactivate_latest_authorization(user):
    latest_date, _, _ = get_latest_authorization(user)

    if not latest_date:
        logger.debug("[deactivate_latest_authorization] No authorizations found for user")
        return

    latest_auth = max(user.authorizations, key=lambda a: a.authorization_date)
    latest_auth.authorization_activeness = "NOAKTIV"
    db.session.commit()
    logger.info(f"[deactivate_latest_authorization] Deactivated authorization id={latest_auth.id} for user MAC={user.MAC}")

def deactivate_latest_authorization_for_mac(mac: str):
    latest = (
        UserAuthorization.query
        .filter_by(user_mac=mac, authorization_activeness='AKTIV')
        .order_by(UserAuthorization.authorization_date.desc())
        .first()
    )
    if not latest:
        logger.debug(f"[deactivate_latest_authorization_for_mac] No active authorization to deactivate for MAC={mac}")
        return

    latest.authorization_activeness = "NOAKTIV"
    db.session.commit()
    logger.info(f"[deactivate_latest_authorization_for_mac] Deactivated authorization id={latest.id} for MAC={mac}")


def convert_limit(limit_str: str) -> timedelta | None:
    if not limit_str:
        return None
    limit_str = limit_str.lower().strip()
    if limit_str in {'teacher', 'student', 'guest'}:
        return None
    
    num, unit = limit_str.split()
    num = int(num)
    unit = unit.rstrip('s')  
    sec_map = {
        'minute': 60,
        'hour': 3600,
        'day': 86400,
        'week': 604800,
        'month': 2592000
    }
    return timedelta(seconds=num * sec_map[unit])


def format_timedelta(td: timedelta) -> str:
    total = int(td.total_seconds())
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)

    parts = []
    if days:
        parts.append(f"{days} kun")
    if hours:
        parts.append(f"{hours} soat")
    if minutes or not parts:
        parts.append(f"{minutes} minut")
    return " ".join(parts)
    

def mikrotik_session_info(mac: str) -> dict:
    mac = mac.upper() 
    pool = None

    try:
        pool = RouterOsApiPool(
            host            = Config.MIKROTIK_HOST,
            username        = Config.MIKROTIK_USER,
            password        = Config.MIKROTIK_PASSWORD,
            port            = 1813,
            use_ssl         = False,
            plaintext_login = True
        )

        api  = pool.get_api()

        active_rsc = api.get_resource("/ip/hotspot/active")
        active     = active_rsc.get( mac_address=mac )

        if active:
            last_ip = active[0]["address"]
        else:
            last_ip = None

        host_rsc = api.get_resource("/ip/hotspot/host")
        all_hosts = host_rsc.get( mac_address=mac )

        total_sessions = len(all_hosts)

        return {
            "last_ip": last_ip,
            "total_sessions": total_sessions
        }

    except RouterOsApiConnectionError as err:
        print(f"[mikrotik] Connection error: {err}")
        return {
            "last_ip": None,
            "total_sessions": 0,
            "error": "mikrotik_connection_error"
        }
    finally:
        if pool:
            pool.disconnect()


def cleanup_radius(mac):
    try:
        logger.info(f"[RADIUS] Connecting to MySQL for MAC={mac}")
        conn = MySQLdb.connect(
            host=Config.DB_HOST, user=Config.DB_USER, passwd=Config.DB_PASS_RAW,
            db=Config.DB_NAME, charset='utf8', cursorclass=DictCursor
        )
        cur = conn.cursor()
        if radius_auth(mac, mac):
            logger.info(f"[RADIUS] Authenticated, deleting radgroupreply for group tariff_{mac}")
            cur.execute("DELETE FROM radgroupreply WHERE groupname = %s", (f"tariff_{mac}",))
            logger.info(f"[RADIUS] Deleting radusergroup for username {mac}")
            cur.execute("DELETE FROM radusergroup WHERE username = %s", (mac,))
        conn.commit()
        logger.info(f"[RADIUS] Commit complete")
    except Exception as e:
        logger.error(f"[RADIUS] Error cleaning up: {e}")
    finally:
        cur.close()
        conn.close()


def cleanup_mikrotik(mac):
    try:
        logger.info(f"[MikroTik] Connecting to RouterOS API")
        api = RouterOsApiPool(
            Config.MIKROTIK_HOST, username=Config.MIKROTIK_USER,
            password=Config.MIKROTIK_PASSWORD, plaintext_login=True
        )
        hotspot_active = api.get_api().get_resource('/ip/hotspot/active')

        active = hotspot_active.get()
        found = False
        for entry in active:
            if entry.get('user', '').strip().upper() == mac.strip().upper():
                logger.info(f"[MikroTik] Removing active session id={entry['id']} for MAC={mac}")
                try:
                    hotspot_active.remove(id=entry['id'])
                except Exception as e:
                    logger.warning(f"[MikroTik] Tried to remove non-existent active session: {e}")
                found = True
                break
        if not found:
            hotspot_host = api.get_api().get_resource('/ip/hotspot/host')
            hosts = hotspot_host.get()
            for host in hosts:
                if host.get('mac-address', '').strip().upper() == mac.strip().upper():
                    logger.info(f"[MikroTik] Removing host id={host['id']} for MAC={mac}")
                    try:
                        hotspot_host.remove(id=host['id'])
                    except Exception as e:
                        logger.warning(f"[MikroTik] Tried to remove non-existent host: {e}")
                    break

        api.disconnect()
        logger.info(f"[MikroTik] Disconnected from RouterOS")
    except Exception as e:
        logger.error(f"[MikroTik] Error cleaning up: {e}")


def format_timedelta(td: timedelta) -> str:
    total = int(td.total_seconds())
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)

    parts = []
    if days:
        parts.append(f"{days} kun")
    if hours:
        parts.append(f"{hours} soat")
    if minutes or not parts:
        parts.append(f"{minutes} minut")
    return " ".join(parts)
    

def mikrotik_session_info(mac: str) -> dict:
    mac = mac.upper() 
    pool = None

    try:
        pool = RouterOsApiPool(
            host            = Config.MIKROTIK_HOST,
            username        = Config.MIKROTIK_USER,
            password        = Config.MIKROTIK_PASSWORD,
            port            = 1813,
            use_ssl         = False,
            plaintext_login = True
        )

        api  = pool.get_api()

        active_rsc = api.get_resource("/ip/hotspot/active")
        active     = active_rsc.get( mac_address=mac )

        if active:
            last_ip = active[0]["address"]
        else:
            last_ip = None

        host_rsc = api.get_resource("/ip/hotspot/host")
        all_hosts = host_rsc.get( mac_address=mac )

        total_sessions = len(all_hosts)

        return {
            "last_ip": last_ip,
            "total_sessions": total_sessions
        }

    except RouterOsApiConnectionError as err:
        print(f"[mikrotik] Connection error: {err}")
        return {
            "last_ip": None,
            "total_sessions": 0,
            "error": "mikrotik_connection_error"
        }
    finally:
        if pool:
            pool.disconnect()
