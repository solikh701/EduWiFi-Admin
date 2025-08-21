from celery import Celery
from app import create_app

def make_celery(flask_app):
    celery = Celery(
        flask_app.import_name,
        broker=flask_app.config["CELERY"]["broker_url"],
        backend=flask_app.config["CELERY"]["result_backend"],
    )
    celery.conf.update(flask_app.config["CELERY"])

    class ContextTask(celery.Task):
        abstract = True
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return super().__call__(*args, **kwargs)

    celery.Task = ContextTask
    return celery

_env = "dev"
celery_app = make_celery(create_app(_env))
