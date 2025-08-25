from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_caching import Cache
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_socketio import SocketIO
import redis
import os

from pymongo import MongoClient, ASCENDING

MONGO_URI     = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "zeekdb")
MONGO_COLL    = os.getenv("MONGO_COLL", "monitoring")
MONGO_TTL_DAYS = int(os.getenv("MONGO_TTL_DAYS", "30"))

mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB_NAME]
monitoring_coll = mongo_db[MONGO_COLL]

def _ensure_mongo_indexes():
    try:
        monitoring_coll.create_index([("ts", ASCENDING)], expireAfterSeconds=MONGO_TTL_DAYS*24*3600)
    except Exception:
        pass
    for f in ("client_ip", "mac", "domain", "protocol"):
        try: monitoring_coll.create_index([(f, ASCENDING)])
        except Exception: pass
    try:
        monitoring_coll.create_index([("uid", ASCENDING), ("protocol", ASCENDING)], unique=True)
    except Exception:
        pass

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
migrate = Migrate()
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
    message_queue="redis://127.0.0.1:6379/0"
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
    migrate.init_app(app, db) 
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

    _ensure_mongo_indexes()
