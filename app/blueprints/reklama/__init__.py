from flask import Blueprint

reklama_bp = Blueprint('reklama', __name__, url_prefix='/')

from . import routes 