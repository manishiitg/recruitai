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

from app.publisher.datasync import sendMessage
from app.publisher.filter import sendBlockingMessage as sendFilterMessage
from app.publisher.stats import sendMessage as sendStatsMessage
from app.util import check_and_validate_account

bp = Blueprint('datasync', __name__, url_prefix='/datasync')

import time

import random

@bp.route("/stats" , methods=["GET"])
@check_and_validate_account
def stats():
    for i in range(10):
        sendStatsMessage({
            "action" : "ping",
            "sleep" : 1,
            "index" : i,
            "priority" : random.randint(0, 10),
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

    return jsonify({}) , 200


@bp.route('/filter/get/candidate_score/<string:id>', methods=['GET'])
@check_and_validate_account
def candidate_score(id):
    
    try:

        ret = sendFilterMessage({
            "id" : id,
            "action" : "candidate_score",
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify(ret), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/filter/get/experiance/display', methods=['GET'])
@check_and_validate_account
def get_exp_display():
    
    try:

        ret = sendFilterMessage({
            "action" : "get_exp_display",
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify(ret), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/filter/get/education/display', methods=['GET'])
@bp.route('/filter/get/education/display/<string:degree>', methods=['GET'])
@check_and_validate_account
def education_display(degree = ""):
    
    try:

        ret = sendFilterMessage({
            "degree" : degree,
            "action" : "get_education_display",
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify(ret), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500



@bp.route('/filter/index/<string:id>/<string:fetch>', methods=['GET'])
@check_and_validate_account
def filter_index(id,fetch):
    
    try:

        ret = sendFilterMessage({
            "id" : id,
            "fetch" : fetch,
            "action" : "index",
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify(ret), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500

# @bp.route('/filter/fetch/<string:id>/<string:fetch>', methods=['GET'])
@bp.route('/filter/fetch/<string:id>/<string:fetch>/<string:page>', methods=['GET'])
@bp.route('/filter/fetch/<string:id>/<string:fetch>/<string:page>/<string:tags>/<string:ai>', methods=['GET', 'POST'])
@check_and_validate_account
def filter_fetch(id,fetch, tags = "", page = 0, limit = 50, ai = ""):

    if ai == "True" or ai == "1" or ai == "true":
        ai = True
    else:
        ai = False

    try:
        if len(tags.strip()) > 0:
            tags = tags.split(",")

        filter = {}

        if request.method == 'POST':
            filter = request.json['filter']
            logger.info("filter %s", filter)

        ret = sendFilterMessage({
            "id" : id,
            "fetch" : fetch,
            "page" : page,
            "limit" : limit,
            "tags" : tags,
            "action" : "fetch",
            "filter" : filter,
            "ai" : ai,
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify(ret), 200
    
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500

@bp.route('/candidate/<string:id>', methods=['GET'])
@bp.route('/candidate/<string:id>/<string:field>', methods=['POST'])
@check_and_validate_account
def candidate(id, field = ""):
    logger.info("got candidate %s", id)

    try:

        if request.method == 'POST':
            doc = request.json['data']
            logger.info("full doc %s", doc)

        sendMessage({
            "id" : id,
            "field" : field,
            "doc" : doc,
            "action" : "syncCandidate",
            "cur_time" : time.time(),
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify([]), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500

@bp.route('/classify-moved/<string:id>/<string:from_id>/<string:to_id>', methods=['GET'])
@check_and_validate_account
def classifyMoved(candidate_id, from_id, to_id):
    logger.info("got job profile from %s", from_id)
    logger.info("got job profile to %s", to_id)

    try:

        sendMessage({
            "candidate_id" : candidate_id,
            "from_id" : from_id,
            "to_id" : to_id,
            "action" : "classifyMoved",
            "cur_time" : time.time(),
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify([]), 200
    
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500

@bp.route('/job-profile-moved/<string:candidate_id>/<string:from_id>/<string:to_id>', methods=['GET'])
@check_and_validate_account
def jobprofileMoved(candidate_id, from_id, to_id):
    logger.info("got job profile from %s", from_id)
    logger.info("got job profile to %s", to_id)

    try:

        sendMessage({
            "candidate_id" : candidate_id,
            "from_id" : from_id,
            "to_id" : to_id,
            "action" : "syncJobProfileChange",
            "cur_time" : time.time(),
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify([]), 200
    
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/job-profile/<string:id>', methods=['GET'])
@check_and_validate_account
def jobprofile(id):
    logger.info("got job profile id %s", id)

    try:

        sendMessage({
            "id" : id,
            "action" : "syncJobProfile",
            "cur_time" : time.time(),
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify([]), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/full', methods=['GET'])
@check_and_validate_account
def full():

    try:

        sendMessage({
            "action" : "full",
            "cur_time" : time.time(),
            "account_name": request.account_name,
            "account_config" : request.account_config
        })

        return jsonify([]), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500