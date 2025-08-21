import json
import redis
from flask import current_app
from .models import UserAuthorization
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from .functions import deactivate_latest_authorization_for_mac

redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)
try:
    redis_client.ping()
    redis_client.config_set('notify-keyspace-events', 'Ex')
except redis.ConnectionError as e:
    raise RuntimeError(f"Cannot connect to Redis: {e}")


def parse_duration(duration_str) -> timedelta:
    s = str(duration_str).strip()
    parts = s.split()
    if len(parts) == 1 and parts[0].isdigit():
        return timedelta(minutes=int(parts[0]))

    if len(parts) != 2:
        return timedelta()

    num_str, unit = parts
    try:
        num = int(num_str)
    except ValueError:
        return timedelta()

    unit = unit.lower().rstrip('s') 

    if unit == 'minute':
        return timedelta(minutes=num)
    if unit == 'hour':
        return timedelta(hours=num)
    if unit == 'day':
        return timedelta(days=num)
    if unit == 'week':
        return timedelta(weeks=num)
    if unit == 'month':
        return relativedelta(months=num)

    return timedelta()


def duration_to_seconds(delta):
    if isinstance(delta, timedelta):
        return int(delta.total_seconds())
    elif isinstance(delta, relativedelta):
        now = datetime.now()
        later = now + delta
        return int((later - now).total_seconds())
    else:
        return 0


def set_user_tariff(mac_address: str, tariff_id: str, duration_str: str):
    print(f"[DEBUG] set_user_tariff: {mac_address=}, {tariff_id=}, {duration_str=}")
    delta = parse_duration(duration_str)
    ttl = duration_to_seconds(delta)
    print(f"[DEBUG] delta={delta}, ttl={ttl}")
    key = f"tariff:{mac_address}"
    if ttl > 0:
        redis_client.setex(key, ttl, tariff_id)
        print(f"[DEBUG] SetEX {key=} {ttl=}")
    else:
        print(f"[WARN] TTL zero or negative, removing {key}")
        remove_user_tariff(mac_address)
        deactivate_latest_authorization_for_mac(mac_address)


def remove_user_tariff(mac_address: str):
    redis_client.delete(f"tariff:{mac_address}")


def reload_all_active_tariffs():
    active_auths = UserAuthorization.query.filter(
        UserAuthorization.authorization_activeness == 'AKTIV'
    ).all()

    for auth in active_auths:
        set_user_tariff(auth.user_mac, auth.selected_tariff, auth.tariff_limit)

def _conn():
    return redis.from_url(current_app.config["SOCKETIO_REDIS_URL"], decode_responses=True)

def rget(key: str):
    return _conn().get(key)

def rset(key: str, value, ttl: int = 300):
    s = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    _conn().setex(key, ttl, s)

def publish(channel: str, payload):
    if not isinstance(payload, str):
        payload = json.dumps(payload, ensure_ascii=False)
    _conn().publish(channel, payload)

def delete_pattern(pattern: str):
    r = _conn()
    for k in r.scan_iter(match=pattern, count=1000):
        r.delete(k)
