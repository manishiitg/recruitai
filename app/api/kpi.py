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

bp = Blueprint('kpi', __name__, url_prefix='/kpi')


@bp.route('', methods=['POST', 'GET'])
@bp.route('/<string:id>', methods=['PUT', 'DELETE'])
@jwt_required
@token.admin_required
def kpi(id=None):
    return jsonify(""), 200