from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_caching import Cache
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from sqlalchemy import create_engine
from flask_socketio import SocketIO
import redis
import os

from urllib.parse import quote_plus
from sqlalchemy import create_engine

MONITORING_DB_USER = os.getenv("MONITORING_DB_USER")
MONITORING_DB_PASS = quote_plus(os.getenv("MONITORING_DB_PASS", ""))
MONITORING_DB_HOST = os.getenv("MONITORING_DB_HOST")
MONITORING_DB_NAME = os.getenv("MONITORING_DB_NAME")

moni_db = create_engine(
    f"mysql+pymysql://{MONITORING_DB_USER}:{MONITORING_DB_PASS}@{MONITORING_DB_HOST}/{MONITORING_DB_NAME}?charset=utf8mb4",
    pool_pre_ping=True
)

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
cors = CORS()
cache = Cache()
sess = Session()
limiter = Limiter(key_func=get_remote_address)
redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)

socketio = SocketIO(
    async_mode="eventlet",
    cors_allowed_origins="*",
    ping_interval=25,
    ping_timeout=60,
)

_redis = None

def get_redis(app=None):
    global _redis
    if _redis is None:
        from flask import current_app
        cfg = (app or current_app).config
        _redis = redis.from_url(cfg["SOCKETIO_REDIS_URL"], decode_responses=True)
    return _redis

def init_extensions(app):
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)
    cache.init_app(app)

    app.config.setdefault("SESSION_REDIS_URL", app.config.get("SOCKETIO_REDIS_URL"))
    app.config["SESSION_REDIS"] = redis.from_url(
        app.config["SESSION_REDIS_URL"], decode_responses=False
    )
    sess.init_app(app)

    uri = app.config.get("RATELIMIT_STORAGE_URI")
    if uri and "RATELIMIT_STORAGE_URL" not in app.config:
        app.config["RATELIMIT_STORAGE_URL"] = uri 

    limiter.init_app(app)

    socketio.init_app(
        app,
        cors_allowed_origins="*",
        message_queue=app.config["SOCKETIO_MESSAGE_QUEUE"],
        ping_interval=25,
        ping_timeout=60,
    )
