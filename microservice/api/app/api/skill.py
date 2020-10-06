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

from app.publisher.skill import sendBlockingMessage
from app.util import check_and_validate_account

bp = Blueprint('skill', __name__, url_prefix='/skill')

@bp.route('/match/<string:keyword>', methods=['GET'])
@bp.route('/match/<string:keyword>/<string:domain>', methods=['GET'])
@check_and_validate_account
def match_similar(keyword, domain = None):
    logger.info("got match %s", keyword)
    try:

        if domain:
            similar = sendBlockingMessage({
                "text" : keyword,
                "match" : True,
                "domain" : domain,
                "account_name": request.account_name,
                "account_config" : request.account_config
            })
        else:
            similar = sendBlockingMessage({
                "text" : keyword,
                "match" : True,
                "account_name": request.account_name,
                "account_config" : request.account_config
            })
        return jsonify(similar), 200
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500
        
# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
@bp.route('/<string:keyword>', methods=['GET'])
@bp.route('/<string:keyword>/<string:domain>', methods=['GET'])
@check_and_validate_account
def similar(keyword, domain = None):
    logger.info("got keyword %s", keyword)
    try:

        if domain:
            similar = sendBlockingMessage({
                "keyword" : keyword,
                "domain" : domain,
                "account_name": request.account_name,
                "account_config" : request.account_config
            })
        else:
            similar = sendBlockingMessage({
                "keyword" : keyword,
                "account_name": request.account_name,
                "account_config" : request.account_config
            })
        return jsonify(similar), 200
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500

@bp.route('/domain_list', methods=['GET'])
@check_and_validate_account
def domain_list():
    logger.info("domain_list")
    try:

        similar = sendBlockingMessage({
            "domain_list" : True,
            "account_name": request.account_name,
            "account_config" : request.account_config
        })
        return jsonify(similar), 200
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500

# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
@bp.route('/global/<string:keyword>', methods=['GET'])
@check_and_validate_account
def similarGlobal(keyword):
    logger.info("got keyword %s", keyword)
    try:
        similar = sendBlockingMessage({
            "keyword" : keyword, 
            "isGlobal": True,
            "account_name": request.account_name,
            "account_config" : request.account_config
        })
        return jsonify(similar), 200
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500
