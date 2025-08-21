from flask import Blueprint

tariff_bp = Blueprint('tariff', __name__, url_prefix='/')

from . import routes 