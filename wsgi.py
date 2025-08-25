import os
import logging
from app import create_app
from app.extensions import socketio
from app.redis_utils import reload_all_active_tariffs

env = "dev" if os.getenv("FLASK_ENV", "prod").startswith("dev") else "prod"
app = create_app(env)

try:
    with app.app_context():
        reload_all_active_tariffs()
except Exception:
    app.logger.exception("bootstrap reload_all_active_tariffs failed")


@app.after_request
def remove_server_header(response):
    response.headers["Server"] = "EduWiFi Gateway"
    if "X-Powered-By" in response.headers:
        del response.headers["X-Powered-By"]
    return response


if __name__ == "__main__":
    socketio.run(app, host="127.0.0.1", port=5050)
