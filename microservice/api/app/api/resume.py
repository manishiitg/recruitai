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

import requests

bp = Blueprint('resume', __name__, url_prefix='/resume')

@bp.route('/<string:filename>', methods=['GET','POST'])
@bp.route('/<string:filename>/<string:mongoid>', methods=['GET','POST'])
@bp.route('/<string:filename>/<string:mongoid>/<string:skills>', methods=['GET','POST'])
def fullparsing(filename, mongoid = None, skills = None):

    meta = {}

    if request.method == 'POST':
        meta = request.json['data']
        logger.info(meta)

    sendMessage({
        "filename" : filename,
        "mongoid" : mongoid,
        "skills" : skills,
        "meta" : meta
    })

    if "instant" in meta:
        if "callback_url" in meta:
            meta["org_request"] = {
                "filename" : filename,
                "mongoid" : mongoid,
                "skills" : skills
            }
            logger.info("acalling callback url %s", meta["callback_url"])
            r = requests.post(meta["callback_url"], json=meta)
            return jsonify(r.status_code), 200


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
