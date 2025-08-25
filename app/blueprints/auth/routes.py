from __future__ import annotations

import re
import logging
from decimal import Decimal
from typing import Dict, Any, Iterable
from datetime import date, timedelta
from urllib.parse import urlparse

from flask import request, jsonify
from sqlalchemy import text

from . import auth_bp
from ...extensions import db, cache, limiter
from ...models import User, Transaction
from werkzeug.exceptions import RequestEntityTooLarge

try:
    from ...env import users as env_users
except Exception:
    env_users = {"admin": "admin", "password": "admin"}

logger = logging.getLogger("app.auth")

# ✅ kesh versiyasi yangilandi
_DASHBOARD_CACHE_KEY = "dashboard:v2"
_DASHBOARD_TTL = 30

def _to_number(v):
    if v is None:
        return 0
    if isinstance(v, Decimal):
        return float(v)
    return v

def _sld_from_url(url: str) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url).hostname
        if not host and "://" not in url:
            host = urlparse("http://" + url).hostname
        if not host:
            return None
        parts = host.split(".")
        if len(parts) >= 2:
            return parts[-2]
        return host
    except Exception:
        return None

def _parse_amount(v) -> int:
    """'5 000 so\'m' -> 5000, '20,000' -> 20000, Decimal -> int."""
    if v is None:
        return 0
    if isinstance(v, (int, float, Decimal)):
        try:
            return int(v)
        except Exception:
            return int(float(v))
    s = re.sub(r"[^\d]", "", str(v))
    return int(s) if s else 0

@auth_bp.errorhandler(RequestEntityTooLarge)
def handle_large_request(e):
    return jsonify({"error": "File size exceeds the allowed limit of 500 MB."}), 413

@auth_bp.route("/api/login", methods=["POST"])
@limiter.limit("8 per minute; 40 per hour")
def login():
    data = request.get_json(silent=True) or {}
    login_name = (data.get("login") or "").strip()
    password = data.get("password") or ""
    logger.debug("[login] Attempted login with login=%s", login_name)
    if login_name == env_users.get("admin") and password == env_users.get("password"):
        logger.info("[login] Admin login successful")
        return jsonify({"success": True}), 200
    logger.warning("[login] Invalid login attempt: login=%s", login_name)
    return jsonify({"success": False, "message": "Invalid login or password"}), 400

@auth_bp.route("/api/dashboard", methods=["GET"])
@limiter.limit("30 per minute")
def dashboard_data():
    cached = cache.get(_DASHBOARD_CACHE_KEY)
    if cached is not None:
        return jsonify(cached)

    # === Umumiy ulanishlar
    total_connections = db.session.execute(
        text("SELECT COUNT(*) FROM user_authorization")
    ).scalar() or 0

    # === User -> domen (universitet) map + wifi set
    user_rows = db.session.execute(text(
        """
        SELECT phone_number, link_login
        FROM user
        WHERE link_login IS NOT NULL AND link_login != ''
        """
    )).fetchall()

    phone_to_domain: Dict[str, str] = {}
    wifi_domains = set()
    for phone_number, link in user_rows:
        dom = _sld_from_url(link)
        if dom:
            phone_to_domain[str(phone_number)] = dom
            wifi_domains.add(dom)
    total_wifi = len(wifi_domains)

    # === Faqat SUCCESS tranzaksiyalar
    success_cond = "LOWER(TRIM(COALESCE(status,''))) = 'success'"

    # === Daromadlar: bugun va oxirgi 30 kun
    today_rows = db.session.execute(text(
        f"""
        SELECT amount FROM transaction
        WHERE DATE(create_time) = CURDATE()
          AND {success_cond}
        """
    )).fetchall()
    daily_income = sum(_parse_amount(a) for (a,) in today_rows)

    last30_rows = db.session.execute(text(
        f"""
        SELECT amount FROM transaction
        WHERE create_time >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
          AND {success_cond}
        """
    )).fetchall()
    monthly_income = sum(_parse_amount(a) for (a,) in last30_rows)

    # === Ulanishlar (legacy 12 oy) — orqaga moslik
    connections_by_month_rows = db.session.execute(text(
        """
        SELECT DATE_FORMAT(authorization_date, '%Y-%m') AS ym, COUNT(*) AS cnt
        FROM user_authorization
        WHERE authorization_date >= DATE_SUB(CURDATE(), INTERVAL 11 MONTH)
        GROUP BY ym
        ORDER BY ym
        """
    )).fetchall()
    ym_to_count = {ym: int(cnt) for ym, cnt in connections_by_month_rows}

    def last_12_month_keys():
        y = date.today().year
        m = date.today().month
        keys = []
        for _ in range(12):
            keys.append(f"{y:04d}-{m:02d}")
            m -= 1
            if m == 0:
                m = 12
                y -= 1
        keys.reverse()
        return keys

    connections_chart = [ym_to_count.get(k, 0) for k in last_12_month_keys()]

    # === Ulanishlar: Yil/Oy/Kun seriyalari
    day_rows = db.session.execute(text(
        """
        SELECT DATE(authorization_date) AS d, COUNT(*) AS cnt
        FROM user_authorization
        WHERE authorization_date >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        GROUP BY d
        ORDER BY d
        """
    )).fetchall()
    day_map = {d.strftime("%Y-%m-%d"): int(cnt) for d, cnt in day_rows}
    last7 = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
    day_labels = [str(d.day) for d in last7]
    day_keys = [d.strftime("%Y-%m-%d") for d in last7]
    day_data = [day_map.get(k, 0) for k in day_keys]

    mon_rows = db.session.execute(text(
        """
        SELECT MONTH(authorization_date) AS m, COUNT(*) AS cnt
        FROM user_authorization
        WHERE YEAR(authorization_date) = YEAR(CURDATE())
        GROUP BY m
        ORDER BY m
        """
    )).fetchall()
    mon_map = {int(m): int(cnt) for m, cnt in mon_rows}
    uz_mon = ['Yan','Fev','Mar','Apr','May','Iyn','Iyl','Avg','Sen','Okt','Noy','Dek']
    mon_labels = uz_mon
    mon_data = [mon_map.get(i+1, 0) for i in range(12)]

    yr_rows = db.session.execute(text(
        """
        SELECT YEAR(authorization_date) AS y, COUNT(*) AS cnt
        FROM user_authorization
        WHERE authorization_date >= DATE_SUB(CURDATE(), INTERVAL 4 YEAR)
        GROUP BY y
        ORDER BY y
        """
    )).fetchall()
    this_year = date.today().year
    year_labels = [str(this_year - 4 + i) for i in range(5)]
    yr_map = {str(int(y)): int(cnt) for y, cnt in yr_rows}
    year_data = [yr_map.get(lbl, 0) for lbl in year_labels]

    connections_series = {
        "day":   {"labels": day_labels,  "data": day_data},
        "month": {"labels": mon_labels,  "data": mon_data},
        "year":  {"labels": year_labels, "data": year_data},
    }

    # === WiFi bo'yicha ULUSH (pie) — barcha vaqt bo'yicha, faqat SUCCESS
    all_tx = db.session.execute(text(
        f"""
        SELECT phone_number, amount
        FROM transaction
        WHERE {success_cond}
        """
    )).fetchall()
    domain_income: Dict[str, int] = {}
    for phone_number, amt in all_tx:
        dom = phone_to_domain.get(str(phone_number))
        if not dom:
            continue
        domain_income[dom] = domain_income.get(dom, 0) + _parse_amount(amt)
    wifi_income_data = [{"name": dom, "value": amt} for dom, amt in domain_income.items()]

    # === Tushum dinamikasi (universitetlar bo'yicha, stacked bar) — faqat SUCCESS
    domains = sorted(list({*wifi_domains}))

    # Kun (7 kun)
    tx7 = db.session.execute(text(
        f"""
        SELECT phone_number, amount, DATE(create_time) AS d
        FROM transaction
        WHERE create_time >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
          AND {success_cond}
        """
    )).fetchall()
    day_series = {d: [0]*len(day_labels) for d in domains}
    day_index = {k: i for i, k in enumerate(day_keys)}
    for phone_number, amt, d in tx7:
        dom = phone_to_domain.get(str(phone_number))
        if not dom or dom not in day_series:
            continue
        key = d.strftime("%Y-%m-%d")
        if key in day_index:
            day_series[dom][day_index[key]] += _parse_amount(amt)

    # Oy (joriy yil, 12 oy)
    txMon = db.session.execute(text(
        f"""
        SELECT phone_number, amount, MONTH(create_time) AS m
        FROM transaction
        WHERE YEAR(create_time) = YEAR(CURDATE())
          AND {success_cond}
        """
    )).fetchall()
    mon_series = {d: [0]*12 for d in domains}
    for phone_number, amt, m in txMon:
        dom = phone_to_domain.get(str(phone_number))
        if not dom or dom not in mon_series:
            continue
        idx = int(m) - 1
        if 0 <= idx < 12:
            mon_series[dom][idx] += _parse_amount(amt)

    # Yil (oxirgi 5 yil)
    txYr = db.session.execute(text(
        f"""
        SELECT phone_number, amount, YEAR(create_time) AS y
        FROM transaction
        WHERE create_time >= DATE_SUB(CURDATE(), INTERVAL 4 YEAR)
          AND {success_cond}
        """
    )).fetchall()
    yr_series = {d: [0]*5 for d in domains}
    year_index = {int(y): i for i, y in enumerate(range(this_year-4, this_year+1))}
    for phone_number, amt, y in txYr:
        dom = phone_to_domain.get(str(phone_number))
        if not dom or dom not in yr_series:
            continue
        y = int(y)
        if y in year_index:
            yr_series[dom][year_index[y]] += _parse_amount(amt)

    income_dynamic = {
        "day":   {"labels": day_labels,  "series": day_series},
        "month": {"labels": mon_labels,  "series": mon_series},
        "year":  {"labels": year_labels, "series": yr_series},
    }

    result: Dict[str, Any] = {
        "total_connections": int(total_connections),
        "total_wifi": int(total_wifi),
        "daily_income": int(daily_income),
        "monthly_income": int(monthly_income),
        # legacy:
        "connections_chart": connections_chart,
        # new:
        "connections_series": connections_series,
        "wifi_income_data": wifi_income_data,   # agar kerak bo'lsa (pie uchun)
        "income_dynamic": income_dynamic,       # Yil/Oy/Kun, universitetlar bo'yicha
        # jadvallar:
        "new_accounts": [
            {
                "id": u.id,
                "date": str(u.authorizations[-1].authorization_date) if getattr(u, "authorizations", None) else "",
                "user": getattr(u, "fio", ""),
                "account": "Verified" if not getattr(u, "block", False) else "Blocked",
                "username": getattr(u, "phone_number", ""),
            } for u in User.query.order_by(User.id.desc()).limit(5).all()
        ],
        "recent_transactions": [
            {
                "id": t.id,
                "date": str(getattr(t, "create_time", "")),
                "amount": _parse_amount(getattr(t, "amount", 0)),
                "status": getattr(t, "status", ""),
                "desc": getattr(t, "reason", ""),
            } for t in Transaction.query.order_by(Transaction.id.desc()).limit(5).all()
        ],
    }

    cache.set(_DASHBOARD_CACHE_KEY, result, timeout=_DASHBOARD_TTL)
    return jsonify(result)
