from flask import (
    Blueprint, g, request, abort, jsonify
)
from bson.objectid import ObjectId
import requests
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
   return jsonify("")
