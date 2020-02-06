from flask import (
    Blueprint, g, request, abort, jsonify
)
from passlib.hash import pbkdf2_sha256
import jwt
from flask_jwt_extended import (
    jwt_required, create_access_token, get_current_user
)
import re
from bson.objectid import ObjectId
import requests
import datetime
from app.config import URL
from app import mongo
from app import token
from app.util import get_manager_profile
import dateutil.parser
import json
from bson import json_util

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['POST'])
def register():
   hr = mongo.db.hr.find_one({
       "integrate_with_hr": True
   })
   if hr is not None and "integrate_with_hr" in hr:
       return jsonify({'msg': ' Invalid request'}), 500
   else:
       if not request.json:
           abort(500)
   name = request.json.get("name", None)
   username = request.json.get("username", None)
   password = request.json.get("password", None)
   if not name or not username or not password:
       return jsonify({"msg": "Invalid Request"}), 400

   user = mongo.db.users.count({
       "username": username
   })
   if user > 0:
       return jsonify({"msg": "Username already taken"}), 500

   id = mongo.db.users.insert_one({
       "name": name,
       "password": pbkdf2_sha256.hash(password),
       "username": username
   }).inserted_id
   return jsonify(str(id))
