from flask import Blueprint

transactions_bp = Blueprint('transactions', __name__, url_prefix='/')

from . import routes 