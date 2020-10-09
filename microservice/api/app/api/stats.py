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

from app.publisher.statsdata import sendBlockingMessage
from app.util import check_and_validate_account


bp = Blueprint('stats', __name__, url_prefix='/stats')

@bp.route('/queue', methods=['GET'])
@check_and_validate_account
def queue_count():
    ret = sendBlockingMessage({
        "action" : "queue_count",
        "account_name": request.account_name,
        "account_config" : request.account_config
    })
    return jsonify(ret), 200

@bp.route('/current_candidate_status/<string:id>', methods=['GET'])
@check_and_validate_account
def current_candidate_status(id):
    ret = sendBlockingMessage({
        "id" : id,
        "action" : "current_candidate_status",
        "account_name": request.account_name,
        "account_config" : request.account_config
    })
    return jsonify(ret), 200

@bp.route('/current_candidate_status_indepth/<string:id>', methods=['GET'])
@check_and_validate_account
def current_candidate_status_indepth(id):
    ret = sendBlockingMessage({
        "id" : id,
        "action" : "current_candidate_status_indepth",
        "account_name": request.account_name,
        "account_config" : request.account_config
    })
    return jsonify(ret), 200
    
@bp.route('/get_data/<string:action>', methods=['GET'])
@check_and_validate_account
def get_data(action):
    ret = sendBlockingMessage({
        "action" : action,
        "account_name": request.account_name,
        "account_config" : request.account_config
    })
    return jsonify(ret), 200

    
    
        