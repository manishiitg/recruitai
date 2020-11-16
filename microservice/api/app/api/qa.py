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

# from app.publisher.qa import sendMessage
from app.publisher.qa_full import sendMessage as sendFullQA
from app.util import check_and_validate_account

bp = Blueprint('qa', __name__, url_prefix='/qa')

@bp.route('fast/<string:id>', methods=['GET'])
@check_and_validate_account
def qa_parse(id):
    logger.info("got candidate %s", id)

    try:

        sendFullQA({
            "action": "qa_candidate_db",
            "mongoid" : id,
            "parsing" : "fast",
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify([]), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500

@bp.route('full/<string:id>', methods=['GET'])
@check_and_validate_account
def qa_parse_full(id):
    logger.info("got candidate %s", id)

    try:

        sendFullQA({
            "action": "qa_candidate_db",
            "mongoid" : id,
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify([]), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500

@bp.route('mini/<string:id>', methods=['GET'])
@check_and_validate_account
def qa_parse_mini(id):
    logger.info("got candidate %s", id)

    try:

        sendFullQA({
            "action": "qa_candidate_db",
            "mongoid" : id,
            "parsing" : "mini",
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify([]), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500