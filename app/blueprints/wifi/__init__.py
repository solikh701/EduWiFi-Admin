from flask import Blueprint

wifi_bp = Blueprint('wifi', __name__, url_prefix='/')

from . import routes 