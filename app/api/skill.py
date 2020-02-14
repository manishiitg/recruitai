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

from app.skillsword2vec.start import get_similar

bp = Blueprint('skill', __name__, url_prefix='/skill')

from app.logging import logger

# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
@bp.route('/<string:keyword>', methods=['GET'])
def similar(keyword):
    logger.info("got keyword %s", keyword)
    try:
        
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
                serializedPositiveSkill.extend(skill.lower().split(" "))
            else:
                serializedPositiveSkill.append(skill.lower())

        serializedNegativeSkill = []
        for skill in negative:
            if " " in skill:
                serializedNegativeSkill.extend(skill.lower().split(" "))
            else:
                serializedNegativeSkill.append(skill.lower())

        logger.info("positive %s and negative %s", serializedPositiveSkill, serializedNegativeSkill)
           
        similar = get_similar(positive, negative)
        return jsonify(similar), 200
    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500
