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

bp = Blueprint('dataset', __name__, url_prefix='/dataset')

@bp.route('/issue', methods=['POST'])
def candidate(id):

    issuetype = request.json.get('type', None)

    # issuetype are NER, CLASSIFY, EMAILCLASSIFY, IMAGEVIZ      
    # 
    # # not used right now  

    return jsonify(""), 200