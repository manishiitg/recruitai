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

bp = Blueprint('datasync', __name__, url_prefix='/datasync')


@bp.route('/filter/get/candidate_score/<string:id>', methods=['GET'])
def candidate_score(id):
    
    try:

        ret = sendFilterMessage({
            "id" : id,
            "action" : "candidate_score"
        })

        return jsonify(ret), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/filter/get/education/display', methods=['GET'])
@bp.route('/filter/get/education/display/<string:degree>', methods=['GET'])
def education_display(degree = ""):
    
    try:

        ret = sendFilterMessage({
            "degree" : degree,
            "action" : "get_education_display"
        })

        return jsonify(ret), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500



@bp.route('/filter/index/<string:id>/<string:fetch>', methods=['GET'])
def filter_index(id,fetch):
    
    try:

        sendFilterMessage({
            "id" : id,
            "fetch" : fetch,
            "action" : "index"
        })

        return jsonify([]), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500

@bp.route('/filter/fetch/<string:id>/<string:fetch>', methods=['GET'])
def filter_fetch(id,fetch):
    

    try:

        ret = sendFilterMessage({
            "id" : id,
            "fetch" : fetch,
            "action" : "fetch"
        })

        return jsonify(ret), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500

@bp.route('/candidate/<string:id>', methods=['GET'])
def candidate(id):
    logger.info("got candidate %s", id)

    try:

        sendMessage({
            "id" : id,
            "action" : "syncCandidate"
        })

        return jsonify([]), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500

@bp.route('/classify-moved/<string:id>/<string:from_id>/<string:to_id>', methods=['GET'])
def classifyMoved(candidate_id, from_id, to_id):
    logger.info("got job profile from %s", from_id)
    logger.info("got job profile to %s", to_id)

    try:

        sendMessage({
            "candidate_id" : candidate_id,
            "from_id" : from_id,
            "to_id" : to_id,
            "action" : "classifyMoved"
        })

        return jsonify([]), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500

@bp.route('/job-profile-moved/<string:id>/<string:from_id>/<string:to_id>', methods=['GET'])
def jobprofileMoved(candidate_id, from_id, to_id):
    logger.info("got job profile from %s", from_id)
    logger.info("got job profile to %s", to_id)

    try:

        sendMessage({
            "candidate_id" : candidate_id,
            "from_id" : from_id,
            "to_id" : to_id,
            "action" : "syncJobProfileChange"
        })

        return jsonify([]), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/job-profile/<string:id>', methods=['GET'])
def jobprofile(id):
    logger.info("got job profile id %s", id)

    try:

        sendMessage({
            "id" : id,
            "action" : "syncJobProfile"
        })

        return jsonify([]), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/full', methods=['GET'])
def full():

    try:

        sendMessage({
            "action" : "full"
        })

        return jsonify([]), 200
    
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500