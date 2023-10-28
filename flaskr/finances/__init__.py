from flask import Blueprint

from . import accounts
from . import budget
from . import dashboard
from . import savings

bp = Blueprint('finances', __name__)

bp.register_blueprint(dashboard.bp)
bp.register_blueprint(savings.bp)
bp.register_blueprint(accounts.bp)
bp.register_blueprint(budget.bp)
