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

bp = Blueprint('training', __name__, url_prefix='/training')

from pathlib import Path

from app.config import BASE_PATH

import uuid

import os
import json

from app.util import check_and_validate_account, get_resume_priority

import shutil

from app.publisher.resume import sendMessage
import time

from app.account import initDB

@bp.route("/resume/requeue/error", methods=["GET"])
@bp.route("/resume/requeue/error/<int:onlycount>", methods=["GET"])
@check_and_validate_account
def requeue_error(only_count = 0):
    db = initDB(request.account_name, request.account_config)

    if only_count == 1:
        count = db.emailStored.count({    
            "cvParsedInfo.error" : { "$exists" : True  }  , 
            "attachment.0.attachment.publicPath" : { "$exists" : True }  }
        )
        return jsonify({
            "count" : count
        })

    count = 0
    rows = db.emailStored.find({    
        "cvParsedInfo.error" : { "$exists" : True  }  , 
        "attachment.0.attachment.publicPath" : { "$exists" : True }  }
    ).limit(500)

    for row in rows:
        count += 1
        priority, days, cur_time = get_resume_priority(int(row["email_timestamp"]) / 1000)
        obj = {
            "filename" : row["attachment"][0]["attachment"]["publicFolder"],
            "mongoid" : str(row["_id"]),
            "skills" : {},
            "meta" : {},
            "priority" : priority,
            "account_name": request.account_name,
            "account_config" : request.account_config
        }
        logger.info(obj)
        sendMessage(obj)
        time.sleep(.1)

    return jsonify({
        "cvParsedInfo_error_false_attachment_public_path_exist_true" : count
    })

@bp.route("/resume/requeue/parsing_fast", methods=["GET"])
@bp.route("/resume/requeue/parsing_fast/<int:only_count>", methods=["GET"])
@check_and_validate_account
def requeue_parsing_fast(only_count = 0):
    db = initDB(request.account_name, request.account_config)

    if only_count == 1:
        count = db.emailStored.count({    
            "cvParsedInfo.parsing_type" : "fast" , 
            "attachment.0.attachment.publicPath" : { "$exists" : True }  }
        )
        return jsonify({
            "count" : count
        })

    count = 0
    rows = db.emailStored.find({    
        "cvParsedInfo.parsing_type" : "fast" , 
        "attachment.0.attachment.publicPath" : { "$exists" : True }  }
    ).limit(1000)

    for row in rows:
        count += 1
        priority, days, cur_time = get_resume_priority(int(row["email_timestamp"]) / 1000)
        obj = {
            "filename" : row["attachment"][0]["attachment"]["publicFolder"],
            "mongoid" : str(row["_id"]),
            "skills" : {},
            "meta" : {},
            "priority" : 1,
            "parsing_type" : "full",
            "account_name": request.account_name,
            "account_config" : request.account_config
        }
        logger.info(obj)
        sendMessage(obj)
        time.sleep(.1)

    return jsonify({
        "cvParsedInfo_error_false_attachment_public_path_exist_true" : count
    })

import random

@bp.route("/resume/requeue/random", methods=["GET"])
@bp.route("/resume/requeue/random/<int:limit>", methods=["GET"])
@check_and_validate_account
def requeue_random(limit = 1):
    db = initDB(request.account_name, request.account_config)
    
    count = db.emailStored.count({    
        "attachment.0.attachment.publicPath" : { "$exists" : True }  }
    ) 
    
    rows = db.emailStored.find({    
        "attachment.0.attachment.publicPath" : { "$exists" : True }  }
    ).limit(limit).skip(random.randint(0, count))

    count = 0
    for row in rows:
        count += 1
        priority, days, cur_time = get_resume_priority(int(row["email_timestamp"]) / 1000)
        obj = {
            "filename" : row["attachment"][0]["attachment"]["publicFolder"],
            "mongoid" : str(row["_id"]),
            "skills" : {},
            "meta" : {},
            "priority" : priority,
            "account_name": request.account_name,
            "account_config" : request.account_config
        }
        logger.info(obj)
        sendMessage(obj)
        time.sleep(.1)
    
    return jsonify({
        "cvParsedInfo_random_attachment_public_path_exist_true" : count
    })

@bp.route("/resume/requeue/candidate/<string:candidate_id>", methods=["GET"])
@check_and_validate_account
def requeue_candidate(candidate_id):
    db = initDB(request.account_name, request.account_config)
    
    
    row = db.emailStored.find_one({    
        "_id" : ObjectId(candidate_id)
    })
    logger.info(row)

    count = 0
    count += 1
    priority, days, cur_time = get_resume_priority(int(row["email_timestamp"]) / 1000)
    obj = {
        "filename" : row["attachment"][0]["attachment"]["publicFolder"],
        "mongoid" : str(row["_id"]),
        "skills" : {},
        "meta" : {},
        "priority" : priority,
        "account_name": request.account_name,
        "account_config" : request.account_config,
    }
    logger.info(obj)
    sendMessage(obj)
    time.sleep(.1)
    
    return jsonify({
        "priority" : priority,
        "email_timestamp" : int(row["email_timestamp"]),
        "days" : days,
    })



@bp.route("/resume/requeue/missed", methods=["GET"])
@bp.route("/resume/requeue/missed/<int:only_count>", methods=["GET"])
@check_and_validate_account
def requeue(only_count = 0):
    db = initDB(request.account_name, request.account_config)
    if only_count == 1:
        count = db.emailStored.count({    
            "cvParsedInfo" : { "$exists" : False  }  , 
            "attachment.0.attachment.publicPath" : { "$exists" : True }  }
        )
        return jsonify({
            "count" : count
        })

    count = 0
    rows = db.emailStored.find({    
        "cvParsedInfo" : { "$exists" : False  }  , 
        "attachment.0.attachment.publicPath" : { "$exists" : True }  }
    ).limit(500)

    for row in rows:
        count += 1
        priority, days, cur_time = get_resume_priority(int(row["email_timestamp"]) / 1000)
        obj = {
            "filename" : row["attachment"][0]["attachment"]["publicFolder"],
            "mongoid" : str(row["_id"]),
            "skills" : {},
            "meta" : {},
            "priority" : priority,
            "account_name": request.account_name,
            "account_config" : request.account_config
        }
        logger.info(obj)
        sendMessage(obj)
        time.sleep(.1)

    return jsonify({
        "cvParsedInfo_exists_false_attachment_public_path_exist_true" : count
    })


@bp.route('/viz/convert_for_annotation', methods=['GET'])
@check_and_validate_account
def convert_for_annotation():
    db = initDB(request.account_name, request.account_config)

    rows = db.aierrors.find({
        "error" : "IMAGEVIZ",
        "is_processed" : {
            "$exists" : False
        } 
    })

    fileLinks = []
    for row in rows:
        db.aierrors.update({
            "_id" : row["_id"]
        }, {
            "$set" : {
                "is_processed" : True
            }
        })

        fileLinks.append(row["fileLink"])

    return json.dumps(fileLinks, indent=True)


@bp.route('/ner/convert_to_label_studio', methods=['GET'])
@check_and_validate_account
def ner_to_label_studio():

    db = initDB(request.account_name, request.account_config)

    rows = db.aierrors.find({
        "error" : "NER",
        "is_processed" : {
            "$exists" : False
        } 
    })

    lines = []
    tags = []

    version_base_path = BASE_PATH + "/../ner/backup/"

    max_version = 0
    for version in os.listdir(version_base_path):
        v = version.replace("v","")
        v = int(v)
        if v > max_version:
            max_version = v

    # max_version = 1

    exist_max_version_path = BASE_PATH + "/../ner/backup/v" + str(max_version)+"/"

    final_json = json.load(open(exist_max_version_path + 'tasks.json'))

    new_max_version_path = BASE_PATH + "/../ner/backup/v" + str(max_version+1)+"/"

    COMPLETION_PATH  = new_max_version_path + "completions/"

    PREDICTION_PATH = new_max_version_path + "predictions/"

    shutil.copytree(exist_max_version_path + "completions", COMPLETION_PATH)

    Path(PREDICTION_PATH).mkdir(parents=True, exist_ok=True)
    
    for row in rows:
        db.aierrors.update({
            "_id" : row["_id"]
        }, {
            "$set" : {
                "is_processed" : True    
            }
            
        })
        if "line" in row and "entity" in row:
            line = row["line"]
            entity = row["entity"]
            isTrue = False

            if "markTrue" in row:
                isTrue = True

            if isTrue:
                result = []

                for tag in entity:
                    res = {
                        "from_name": "ner",
                        "honeypot": True,
                        "id": uuid.uuid4().hex,
                        "source": "$text",
                        "score" : tag["confidence"],
                        "to_name": "text",
                        "type": "labels",
                        "value": {
                            "start": tag["start_pos"],
                            "end": tag["end_pos"],
                            "labels": [
                                tag["type"]
                            ],
                            "text": tag["text"]
                        }
                    }
                    
                    result.append(res)

                completion = {
                    "completions": [{
                        "id": uuid.uuid4().hex,
                        "lead_time": 20,
                        "result": result,
                        "data" : {
                            "text": line
                        },
                        "id": len(final_json),
                        "task_path": "../tasks.json"
                    }]
                }


            
                data = json.dumps(completion, indent=1)
                with open(PREDICTION_PATH + str(len(final_json)) + '.json', 'w') as f:
                    f.write(data)

            obj = {
                "data" : {
                    "text": line,
                    "id": len(final_json)
                }

            }
            final_json[str(len(final_json))] = obj

    
    

    data = json.dumps(final_json, indent=1)
    
    with open(new_max_version_path + 'tasks.json', 'w') as f:
        f.write(data)


    return jsonify({
        "new_max_version_path" : new_max_version_path,
        "count" : len(final_json)
    }), 200
