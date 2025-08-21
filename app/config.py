from urllib.parse import quote_plus
from dotenv import load_dotenv
from pathlib import Path
import os

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

def _env(name: str, *, required: bool = True, default: str | None = None) -> str:
    val = os.getenv(name, default)
    if required and (val is None or val == ""):
        raise RuntimeError(f"Environment variable '{name}' is not set")
    return val or ""

class Config:
    SECRET_KEY     = _env("SECRET_KEY",     required=False, default="dev-secret")
    JWT_SECRET_KEY = _env("JWT_SECRET_KEY", required=False, default="dev-jwt")

    DB_USER     = _env("DB_USER")
    DB_PASS     = _env("DB_PASS")
    DB_PASS_RAW  = _env("DB_PASS",  required=False, default="Admin@2024")
    DB_PASS      = quote_plus(DB_PASS_RAW)
    DB_HOST     = _env("DB_HOST")
    DB_NAME     = _env("DB_NAME")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"
    )

    MYSQLDB_PASSWORD = DB_PASS_RAW
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_size": 20, "max_overflow": 10, "pool_timeout": 30}

    UPLOAD_FOLDER      = os.getenv("UPLOAD_FOLDER", "uploads")
    ALLOWED_EXTENSIONS = [e for e in os.getenv("ALLOWED_EXTENSIONS", "png,jpg,jpeg,pdf").split(",") if e]

    JWT_TOKEN_LOCATION      = ["headers", "cookies"]
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_ACCESS_COOKIE_NAME  = "access_token"

    RADIUS_SERVER     = _env("RADIUS_SERVER", required=False, default="")
    RADIUS_PORT       = int(os.getenv("RADIUS_PORT", "1812"))
    RADIUS_SECRET     = (_env("RADIUS_SECRET", required=False, default="").encode("utf-8")
                         if os.getenv("RADIUS_SECRET") else b"")
    RADIUS_DICT_PATHS = _env("RADIUS_DICT_PATHS", required=False, default="")
    HOTSPOT_IP        = _env("HOTSPOT_IP", required=False, default="")

    SOCKETIO_REDIS_URL = os.getenv("SOCKETIO_REDIS_URL", "redis://127.0.0.1:6379/0")

    CACHE_TYPE = "RedisCache"
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "300"))
    CACHE_REDIS_URL = SOCKETIO_REDIS_URL
    CACHE_KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "cache:")

    SESSION_TYPE = "redis"
    SESSION_REDIS_URL = SOCKETIO_REDIS_URL
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True

    RATELIMIT_STORAGE_URI = SOCKETIO_REDIS_URL
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per minute")

    SOCKETIO_MESSAGE_QUEUE = SOCKETIO_REDIS_URL

    CELERY = {
        "broker_url": os.getenv("CELERY_BROKER_URL", SOCKETIO_REDIS_URL),
        "result_backend": os.getenv("CELERY_RESULT_BACKEND", SOCKETIO_REDIS_URL),
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "task_track_started": True,
        "broker_transport_options": {"visibility_timeout": 3600},
        "timezone": os.getenv("TZ", "Asia/Tashkent"),
    }

class DevelopmentConfig(Config):
    DEBUG = True
    ENV   = "development"

class ProductionConfig(Config):
    DEBUG = False
    ENV   = "production"
