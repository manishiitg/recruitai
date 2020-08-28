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

from app.util import check_and_validate_account
from app.publisher.search import sendBlockingMessage
from app.publisher.searchindex import sendMessage

bp = Blueprint('search', __name__, url_prefix='/search')

@bp.route('/addDoc/<string:id>', methods=['POST'])
@bp.route('/addDoc/<string:id>/<string:line>', methods=['GET'])
@check_and_validate_account
def addDocument(id, line=None):
    try:
        if request.method == 'POST':
            data = request.json.get('lines', [])
            meta_data = request.json.get('meta_data', {})
            
            # we are not storing meta any more in elastic search. instead of using redis with datasync

            ret = sendMessage({
                "id": id,
                "lines" : data,
                "extra_data" : {},
                "action" : "addDoc",
                "account_name": request.account_name,
                "account_config" : request.account_config
            })
            # ret = addDoc(id, data, {})

            
        else:
            ret = sendBlockingMessage({
                "id": id,
                "lines" : [line],
                "extra_data" : {},
                "action" : "addDoc",
                "account_name": request.account_name,
                "account_config" : request.account_config
            })
            # ret = addDoc(id, [line], {})

        return jsonify(ret), 200

    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/add-meta/<string:mongoid>', methods=['POST'])
@check_and_validate_account
def addMetaDoc(mongoid):
    try:
        # ret = sendBlockingMessage({
        #     "id": mongoid,
        #     "meta" : request.json.get("data"),
        #     "action" : "addMeta"
        # })
        # return jsonify(ret), 200
        # we are not storing meta any more in elastic search. instead of using redis with datasync
        return jsonify({}), 200
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500

@bp.route('/get-stats', methods=['GET'])
@check_and_validate_account
def getStats():
    try:
        ret = sendBlockingMessage({
            "action" : "stats",
            "account_name": request.account_name,
            "account_config" : request.account_config
        })
        return jsonify(ret), 200
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/deleteDoc/<string:mongoid>', methods=['GET'])
@check_and_validate_account
def deleteDocument(mongoid):
    try:
        ret = sendMessage({
            "id": mongoid,
            "action" : "deleteDoc",
            "account_name": request.account_name,
            "account_config" : request.account_config
        })
        return jsonify(ret), 200
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/getDoc/<string:mongoid>', methods=['GET'])
@check_and_validate_account
def getDocument(mongoid):
    try:
        ret = sendBlockingMessage({
            "id": mongoid,
            "action" : "getDoc",
            "account_name": request.account_name,
            "account_config" : request.account_config
        })
        return jsonify(ret), 200
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/search/<string:search>', methods=['GET'])
@check_and_validate_account
def search(search):
    try:
        ret = sendBlockingMessage({
            "search": search,
            "action" : "searchDoc",
            "account_name": request.account_name,
            "account_config" : request.account_config
        })
        return jsonify(ret), 200
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/deleteAll', methods=['GET'])
@check_and_validate_account
def deleteAllDocument():
    try:
        ret = sendMessage({
            "action" : "deleteAll",
            "account_name": request.account_name,
            "account_config" : request.account_config
        })
        return jsonify(ret), 200
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
