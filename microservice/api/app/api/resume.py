import json
import os
from pathlib import Path
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

from app.publisher.resume import sendMessage
from app.util import check_and_validate_account

import requests
import time

bp = Blueprint('resume', __name__, url_prefix='/resume')

@bp.route('/<string:filename>', methods=['GET','POST'])
@bp.route('/<string:filename>/<string:mongoid>', methods=['GET','POST'])
@bp.route('/<string:filename>/<string:mongoid>/<string:skills>', methods=['GET','POST'])
@bp.route('/<string:filename>/<string:mongoid>/<string:skills>/<int:priority>', methods=['GET','POST'])
@check_and_validate_account
def fullparsing(filename, mongoid = None, skills = None, priority = 0):

    meta = {}

    if request.method == 'POST':
        meta = request.json['data']
        logger.info("meta from api %s", meta)

    
    days = 0
    if "cv_timestamp_seconds" in meta:
        cv_date = meta["cv_timestamp_seconds"]
        cur_time = time.time()

        if cv_date == 0: 
            # manual candidate
            priority = 10
        else:
            days =  abs(cur_time - cv_date)  / (60 * 24 )

            if days < 1:
                priority = 9
            elif days < 7:
                priority = 8
            elif days < 30:
                priority = 7
            elif days < 90:
                priority = 6
            elif days < 365:
                priority = 5
            elif days < 365 * 2:
                priority = 4
            else:
                priority = 1



    sendMessage({
        "filename" : filename,
        "mongoid" : mongoid,
        "skills" : skills,
        "meta" : meta,
        "priority" : priority,
        "account_name": request.account_name,
        "account_config" : request.account_config
    })

    if "instant" in meta:
        if "callback_url" in meta:
            meta["org_request"] = {
                "filename" : filename,
                "mongoid" : mongoid,
                "skills" : skills
            }
            logger.info("acalling callback url %s", meta["callback_url"])
            r = requests.post(meta["callback_url"], json=meta)
            return jsonify(r.status_code), 200


    return jsonify({
        "priority" : priority,
        "server_current_time" : time.time(),
        "days" : days
    }), 200
