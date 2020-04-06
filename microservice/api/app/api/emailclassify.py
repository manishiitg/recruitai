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

from app.publisher.classify import sendBlockingMessage

bp = Blueprint('emailclassify', __name__, url_prefix='/emailclassify')

from app.logging import logger
from app.util import check_and_validate_account

# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
@bp.route('/', methods=[ 'POST'])
@bp.route('/<string:body>/<string:subject>', methods=['GET'])
@check_and_validate_account
def classify(body = None, subject = None):
    try:
        if request.method == 'POST':
            
            return jsonify(sendBlockingMessage([
                {
                    "subject" : request.json.get('subject', ""),
                    "body" : request.json.get('body', ""),
                    "account_name": request.account_name,
                    "account_config" : request.account_config
                }
            ])), 200
        else:
            
            return jsonify(sendBlockingMessage([
                {
                    "subject" : subject,
                    "body" : body,
                    "account_name": request.account_name,
                    "account_config" : request.account_config
                }
            ])), 200
        
    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500
