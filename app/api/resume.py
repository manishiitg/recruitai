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

bp = Blueprint('resume', __name__, url_prefix='/resume')

from app.logging import logger
from app.config import RESUME_UPLOAD_BUCKET, BASE_PATH
from pathlib import Path
import os
import json
from app.detectron.start import processAPI

from app.config import storage_client

# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
@bp.route('/<string:filename>', methods=['GET'])
def parse(filename):

    try:
        

        bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
        blob = bucket.blob(filename)
        dest = BASE_PATH + "/../temp"
        Path(dest).mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(os.path.join(dest, filename))

        response , basePath = processAPI(os.path.join(dest, filename))

        
        return jsonify({
            "basePath": basePath,
            "response": response
        }) , 200
    except Exception as e:
        return jsonify(str(e)) , 500