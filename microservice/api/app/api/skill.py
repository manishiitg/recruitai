from app.logging import logger
from app import token
from app import mongo
from flask import (
    Blueprint, flash, jsonify, abort, request
)

from bson.objectid import ObjectId
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)

from app.publisher.skill import sendBlockingMessage

bp = Blueprint('skill', __name__, url_prefix='/skill')

# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
@bp.route('/<string:keyword>', methods=['GET'])
def similar(keyword):
    logger.info("got keyword %s", keyword)
    try:

        similar = sendBlockingMessage({
            "keyword" : keyword
        })
        return jsonify(similar), 200
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
@bp.route('/global/<string:keyword>', methods=['GET'])
def similarGlobal(keyword):
    logger.info("got keyword %s", keyword)
    try:
        similar = sendBlockingMessage({
            "keyword" : keyword, 
            "isGlobal": True
        })
        return jsonify(similar), 200
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500
