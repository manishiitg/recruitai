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

from app.search.index import addDoc, deleteDoc, searchDoc, deleteAll, getDoc, addMeta

bp = Blueprint('search', __name__, url_prefix='/search')


# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
@bp.route('/addDoc/<string:id>', methods=['POST'])
@bp.route('/addDoc/<string:id>/<string:line>', methods=['GET'])
def addDocument(id, line=None):
    try:
        if request.method == 'POST':
            data = request.json.get('lines', [])
            ret = addDoc(id, data, {})
        else:
            ret = addDoc(id, [line], {})

        return jsonify(ret), 200

    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/add-meta/<string:mongoid>', methods=['POST'])
def addMetaDoc(mongoid):
    try:
        return jsonify(addMeta(mongoid, request.json.get("data"))), 200
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/deleteDoc/<string:mongoid>', methods=['GET'])
def deleteDocument(mongoid):
    try:
        return jsonify(deleteDoc(mongoid)), 200
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/getDoc/<string:mongoid>', methods=['GET'])
def getDocument(mongoid):
    try:
        return jsonify(getDoc(mongoid)), 200
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/search/<string:search>', methods=['GET'])
def search(search):
    try:
        return jsonify(searchDoc(search)), 200
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/deleteAll', methods=['GET'])
def deleteAllDocument():
    try:
        return jsonify(deleteAll()), 200
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500



# @bp.route('/flush', methods=['GET'])
# def flushDocument():
#     try:
#         return jsonify(flush()), 200
#     except Exception as e:
#         logger.critical(e)
#         return jsonify(str(e)), 500


# @bp.route('/refresh', methods=['GET'])
# def refreshDocument():
#     try:
#         return jsonify(refresh()), 200
#     except Exception as e:
#         logger.critical(e)
#         return jsonify(str(e)), 500
