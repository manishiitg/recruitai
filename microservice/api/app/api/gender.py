from app import token
from flask import (
    Blueprint, flash, jsonify, abort, request
)

from bson.objectid import ObjectId
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)

from app.publisher.gender import sendBlockingMessage

bp = Blueprint('gender', __name__, url_prefix='/gender')

from app.logging import logger
from app.util import check_and_validate_account

# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
@bp.route('/<string:name>', methods=['GET'])
@check_and_validate_account
def classify(name = None):
    try:
        return jsonify(sendBlockingMessage(
            {
                "name" : name.lower(),
                "account_name": request.account_name,
                "account_config" : request.account_config
            }
        )), 200
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500
