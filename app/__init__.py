import logging
import os
from flask import Flask
from urllib3 import disable_warnings, exceptions

from app.logging_config import configure_logging
from app.config import DevelopmentConfig, ProductionConfig
from app.extensions import init_extensions

from app.blueprints.wifi import wifi_bp
from app.blueprints.auth import auth_bp
from app.blueprints.users import users_bp
from app.frontend.views import frontend_bp
from app.blueprints.tariff import tariff_bp
from app.blueprints.reklama import reklama_bp
from app.blueprints.settings import settings_bp
from app.blueprints.teachers import teachers_bp
from app.blueprints.monitoring import monitoring_bp
from app.blueprints.transactions import transactions_bp

from app.sockets import init_socketio_handlers, emit_refresh

disable_warnings(exceptions.InsecureRequestWarning)

def create_app(env: str = "dev") -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")

    cfg_cls = DevelopmentConfig if env == "dev" else ProductionConfig
    app.config.from_object(cfg_cls)

    init_extensions(app)

    init_socketio_handlers()

    app.emit_refresh = emit_refresh

    app.register_blueprint(wifi_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(tariff_bp)
    app.register_blueprint(reklama_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(frontend_bp)
    app.register_blueprint(teachers_bp)
    app.register_blueprint(monitoring_bp)
    app.register_blueprint(transactions_bp)

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        configure_logging()
    app.logger = logging.getLogger("app")

    from app import sockets

    return app
