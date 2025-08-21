import os
from app import create_app

env = "dev" if os.getenv("FLASK_ENV", "prod").startswith("dev") else "prod"
app = create_app(env)

try:
    from app.redis_utils import reload_all_active_tariffs
    with app.app_context():
        reload_all_active_tariffs()
except Exception as e:
    app.logger.exception("bootstrap reload_all_active_tariffs failed")
