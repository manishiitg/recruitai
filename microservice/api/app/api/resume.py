import json
import os
from pathlib import Path
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

from app.publisher.resume import sendMessage

bp = Blueprint('resume', __name__, url_prefix='/resume')

@bp.route('/<string:filename>/<string:mongoid>', methods=['GET'])
def fullparsing(filename, mongoid = None):
    sendMessage({
        "filename" : filename,
        "mongoid" : mongoid
    })

    return jsonify(""), 200



# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
# @bp.route('/picture/<string:filename>', methods=['GET'])
# def picture(filename):

#     # try:

#     bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
#     blob = bucket.blob(filename)
#     dest = BASE_PATH + "/../temp"
#     Path(dest).mkdir(parents=True, exist_ok=True)
#     blob.download_to_filename(os.path.join(dest, filename))

#     response, basedir = extractPicture(os.path.join(dest, filename))

#     return jsonify(response, basedir), 200
#     # except Exception as e:
#     #     return jsonify(str(e)) , 500


# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
# @bp.route('/parse/<string:filename>', methods=['GET'])
# def parse(filename):

#     try:

#         bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
#         blob = bucket.blob(filename)
#         dest = BASE_PATH + "/../temp"
#         Path(dest).mkdir(parents=True, exist_ok=True)
#         blob.download_to_filename(os.path.join(dest, filename))

#         response, basePath = processAPI(os.path.join(dest, filename))

#         return jsonify({
#             "basePath": basePath,
#             "response": response
#         }), 200
#     except Exception as e:
#         return jsonify(str(e)), 500
