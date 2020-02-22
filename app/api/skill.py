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

from app.skillsword2vec.start import get_similar , vec_exists

bp = Blueprint('skill', __name__, url_prefix='/skill')


def processWord2VecInput(keyword):
    if "-" in keyword:
        negative = keyword.split("-")[1]
        positive = keyword.split("-")[0]
    else:
        positive = keyword
        negative = []

    if "+" in positive:
        positive = positive.split("+")
    else:
        positive = [positive]

    serializedPositiveSkill = []
    for skill in positive:
        if " " in skill:
            if vec_exists("_".join(skill.lower().split(" "))):
                serializedPositiveSkill.append("_".join(skill.lower().split(" ")))
            else:
                serializedPositiveSkill.extend(skill.lower().split(" "))
        else:
            serializedPositiveSkill.append(skill.lower())

    serializedNegativeSkill = []
    for skill in negative:
        if " " in skill:
            if vec_exists("_".join(skill.lower().split(" "))):
                serializedNegativeSkill.append("_".join(skill.lower().split(" ")))
            else:
                serializedNegativeSkill.extend(skill.lower().split(" "))
        else:
            serializedNegativeSkill.append(skill.lower())

    logger.info("seralized positive %s and negative %s",
                serializedPositiveSkill, serializedNegativeSkill)
    return serializedPositiveSkill,  serializedNegativeSkill


# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
@bp.route('/<string:keyword>', methods=['GET'])
def similar(keyword):
    logger.info("got keyword %s", keyword)
    try:

        serializedPositiveSkill, serializedNegativeSkill = processWord2VecInput(
            keyword)

        similar = get_similar(serializedPositiveSkill, serializedNegativeSkill)
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
        serializedPositiveSkill, serializedNegativeSkill = processWord2VecInput(
            keyword)

        similar = get_similar(serializedPositiveSkill, serializedNegativeSkill, True)
        return jsonify(similar), 200
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500
