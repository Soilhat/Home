import os
import signal

from flask import (
    Blueprint, jsonify
)

bp = Blueprint('system', __name__, url_prefix='/system')

@bp.route('/shutdown')
def shutdown():
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({ "success": True, "message": "Server is shutting down..." })
