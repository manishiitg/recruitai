from functools import wraps
from flask import g, request, jsonify

from app.config import BASE_PATH
from app.logging import logger

import json
import os
import time

account_json_path = os.path.join(BASE_PATH , "account.config.json")

def get_resume_priority(timestamp_seconds):
    cur_time = time.time()
    days = 0
    if timestamp_seconds == 0: 
        # manual candidate
        priority = 10
    else:
        days =  abs(cur_time - timestamp_seconds)  / (60 * 60 * 24 )

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
    
    return priority, days, cur_time

def check_and_validate_account(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        account_name = None

        if "account-name" in request.headers:
            account_name = request.headers['account-name']

        elif "account-name" in request.args:
            account_name = request.args['account-name']

        if account_name is None:
            return jsonify("account-name is mandatory"), 500


        logger.info("account name %s" % account_name)
        
        if not os.path.exists(account_json_path):
            return jsonify("account config not found %s" % account_json_path), 500


        with open(account_json_path) as ff:
            account_config = json.load(ff)

        
        accounts = list(account_config.keys())

        if account_name not in accounts:
            return jsonify("account name not found in list %s" % accounts), 500
                
        request.account_name = account_name
        request.account_config = account_config[account_name]

        return f(*args, **kwargs)
    

    return decorated_function