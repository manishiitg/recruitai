from app import mongo
from app import token
from app.util import serialize_doc
import datetime

from flask import (
    Blueprint, flash, jsonify, abort, request
)

from bson.objectid import ObjectId


from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)

bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/list', methods=['GET'])
@jwt_required
@token.admin_required
def user_list():
    users = mongo.db.users.find({"status": "Enabled"})
    users = [serialize_doc(user) for user in users]
    return jsonify(users), 200