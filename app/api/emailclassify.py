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

from app.emailclassify.start import classifyData

bp = Blueprint('emailclassify', __name__, url_prefix='/emailclassify')

from app.logging import logger

# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
@bp.route('/<string:body>/<string:subject>', methods=['GET', 'POST'])
def classify(body = None, subject = None):
    try:
        if request.method == 'POST':
            data = request.json("data")
            return jsonify(classifyData(data)), 200
        else:
            return jsonify(classifyData([
                {
                    "subject" : subject,
                    "body" : body
                }
            ])), 200
        
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500
