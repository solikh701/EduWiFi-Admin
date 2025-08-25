from flask import Blueprint

authorizations_bp = Blueprint('authorizations', __name__, url_prefix='/')

from . import routes 