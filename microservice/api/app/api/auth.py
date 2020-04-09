from flask import (
    Blueprint, g, request, abort, jsonify
)
from bson.objectid import ObjectId
import requests
# from app import mongo
from app import token
import json
from bson import json_util

bp = Blueprint('auth', __name__, url_prefix='/auth')

from app.util import check_and_validate_account

@bp.route('/ping', methods=['GET', 'POST'])
@check_and_validate_account
def ping():
   return jsonify({
      "pong" : request.account_config
   })

@bp.route('/register', methods=['POST'])
def register():
   return jsonify("")
