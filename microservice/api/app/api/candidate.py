from app.logging import logger
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

from app.publisher.candidate import sendMessage
from app.util import check_and_validate_account

bp = Blueprint('classify', __name__, url_prefix='/classify')

@bp.route('/candidate/<string:id>', methods=['GET'])
@check_and_validate_account
def candidate(id):
    logger.info("got candidate %s", id)

    try:

        sendMessage({
            "mongoid" : id,
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify([]), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500