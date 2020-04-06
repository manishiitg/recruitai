from functools import wraps
from flask import g, request, jsonify

from app.config import BASE_PATH
from app.logging import logger

import json
import os

account_json_path = os.path.join(BASE_PATH , "account.config.json")

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