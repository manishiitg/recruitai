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

from app.publisher.skillextract import sendBlockingMessage
from app.util import check_and_validate_account
from app.publisher.skillindex import sendMessage

bp = Blueprint('skillextract', __name__, url_prefix='/skillextract')

# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required

@bp.route('/<string:mongoid>', methods=['GET'])
@bp.route('/<string:mongoid>/<string:skills>', methods=['GET'])
@check_and_validate_account
def skillextract(mongoid, skills = ""):
    logger.info("got mongo id %s and skills %s", mongoid, skills)
    try:

        similar = sendBlockingMessage({
            "action" : "extractSkill",
            "mongoid" : mongoid,
            "skills" : skills.split(","),
            "account_name": request.account_name,
            "account_config" : request.account_config
        })
        return jsonify(similar), 200
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500

@bp.route('index/<string:mongoid>', methods=['GET'])
@bp.route('index/<string:mongoid>/<string:skills>', methods=['GET'])
@check_and_validate_account
def skillextractindex(mongoid, skills = ""):
    logger.info("got mongo id %s and skills %s", mongoid, skills)
    try:

        similar = sendMessage({
            "action" : "extractSkill",
            "mongoid" : mongoid,
            "skills" : skills.split(","),
            "account_name": request.account_name,
            "account_config" : request.account_config
        })
        return jsonify({}), 200
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500