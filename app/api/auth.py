from flask import (
    Blueprint, g, request, abort, jsonify
)
from bson.objectid import ObjectId
import requests
from app import mongo
from app import token
import json
from bson import json_util

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['POST'])
def register():
   return jsonify("")
