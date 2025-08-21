from flask import Blueprint

teachers_bp = Blueprint('teachers', __name__, url_prefix='/')

from . import routes 