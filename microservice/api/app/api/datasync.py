
import random
import time
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

from app.publisher.filterindex import sendMessage as filterindex
from app.publisher.datasync import sendMessage
from app.publisher.filter import sendBlockingMessage as sendFilterMessage
from app.publisher.stats import sendMessage as sendStatsMessage
from app.util import check_and_validate_account

bp = Blueprint('datasync', __name__, url_prefix='/datasync')


@bp.route("/config", methods=["GET"])
@check_and_validate_account
def config():
    return jsonify(request.account_config), 200


@bp.route("/check_missing_ai_data", methods=["GET"])
@check_and_validate_account
def check_missing_ai_data():
    sendMessage({
        "action": "check_missing_ai_data",
        "account_name": request.account_name,
        "account_config": request.account_config,
        "priority": 10
    })

    return jsonify(""), 200


@bp.route("/stats", methods=["GET"])
@check_and_validate_account
def stats():
    for i in range(10):
        sendStatsMessage({
            "action": "ping",
            "sleep": 1,
            "index": i,
            "priority": random.randint(0, 10),
            "account_name": request.account_name,
            "account_config": request.account_config
        })

    return jsonify({}), 200


@bp.route('/speedup', methods=['POST'])
@check_and_validate_account
def speed_up():

    try:
        if "payload" not in request.json:
            request.json["payload"] = {}

        try:
            ret = sendFilterMessage({
                "action": "speed_up",
                "account_name": request.account_name,
                "account_config": request.account_config,
                "url": request.json["url"],
                "access_token": request.json["access_token"],
                "payload": request.json["payload"]
            })

            return jsonify(ret), 200
        except Exception as e:
            time.sleep(1)
            ret = sendFilterMessage({
                "action": "speed_up",
                "account_name": request.account_name,
                "account_config": request.account_config,
                "url": request.json["url"],
                "access_token": request.json["access_token"],
                "payload": request.json["payload"]
            })

            return jsonify(ret), 200

    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


# @bp.route('/job-overview/tag/<string:tag_id>', methods=['POST'])
# @check_and_validate_account
# def job_overview(tag_id):

#     try:

#         ret = sendFilterMessage({
#             "action" : "job_overview",
#             "account_name": request.account_name,
#             "account_config" : request.account_config,
#             "tag_id" : tag_id,
#             "url" : request.json["url"],
#             "access_token" : request.json["access_token"]
#         })

#         return jsonify(ret), 200

#     except KeyError as e:
#         logger.critical(e)
#         return jsonify(str(e)), 500


@bp.route('/filter/get/candidate_score_bulk/<string:id>', methods=['POST'])
@check_and_validate_account
def candidate_score_bulk(id):

    try:

        data = request.json['data']

        # ret = sendFilterMessage({
        filterindex({
            "id": id,
            "action": "candidate_score_bulk",
            "account_name": request.account_name,
            "account_config": request.account_config,
            "criteria": data
        })

        return jsonify({}), 200

    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/filter/get/candidate_score/<string:id>', methods=['GET', 'POST'])
@check_and_validate_account
def candidate_score(id):

    try:

        if request.method == 'POST':
            print(request.json)
            data = request.json['data']
        else:
            data = {}

        # ret = sendFilterMessage({
        ret = {}
        filterindex({
            "id": id,
            "action": "candidate_score",
            "account_name": request.account_name,
            "account_config": request.account_config,
            "criteria": data
        })

        return jsonify(ret), 200

    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/filter/get/experiance/display', methods=['GET'])
@check_and_validate_account
def get_exp_display():

    try:

        ret = sendFilterMessage({
            "action": "get_exp_display",
            "account_name": request.account_name,
            "account_config": request.account_config
        })

        return jsonify(ret), 200

    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/filter/get/education/display', methods=['GET'])
@bp.route('/filter/get/education/display/<string:degree>', methods=['GET'])
@check_and_validate_account
def education_display(degree=""):

    try:

        ret = sendFilterMessage({
            "degree": degree,
            "action": "get_education_display",
            "account_name": request.account_name,
            "account_config": request.account_config
        })

        return jsonify(ret), 200

    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/filter/index/<string:id>/<string:fetch>', methods=['GET'])
@check_and_validate_account
def filter_index(id, fetch):

    try:

        ret = sendFilterMessage({
            "id": id,
            "fetch": fetch,
            "action": "index",
            "account_name": request.account_name,
            "account_config": request.account_config
        })

        return jsonify(ret), 200

    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/filter/get_candidate_tags', methods=['GET'])
@check_and_validate_account
def get_candidate_tags():
    ret = sendFilterMessage({
        "action": "get_candidate_tags",
        "account_name": request.account_name,
        "account_config": request.account_config
    })

    return jsonify(ret), 200


@bp.route('/filter/index/<string:id>/<string:type>', methods=['GET'])
@check_and_validate_account
def filter_index_new(id, type):
    ret = sendFilterMessage({
        "id": id,
        "fetch": "type",
        "action": "index",
        "account_name": request.account_name,
        "account_config": request.account_config
    })

    return jsonify(ret), 200


@bp.route('/filter/get/<string:tag_id>', methods=['GET'])
@bp.route('/filter/get/<string:tag_id>/<string:job_profile_id>', methods=['GET'])
@check_and_validate_account
def filter_index_get(tag_id, job_profile_id=None):
    ret = sendFilterMessage({
        "tag_id": tag_id,
        "job_profile_id": job_profile_id,
        "action": "filter_index_get",
        "account_name": request.account_name,
        "account_config": request.account_config
    })
    
    return jsonify(ret), 200

# @bp.route('/filter/fetch/<string:id>/<string:fetch>', methods=['GET'])


@bp.route('/filter/fetch/<string:id>/<string:fetch>/<string:page>', methods=['GET'])
@bp.route('/filter/fetch/<string:id>/<string:fetch>/<string:page>/<string:tags>/<string:ai>', methods=['GET', 'POST'])
@bp.route('/filter/fetch/<string:id>/<string:fetch>/<string:page>/<string:tags>/<string:ai>/<string:starred>', methods=['GET', 'POST'])
@bp.route('/filter/fetch/<string:id>/<string:fetch>/<string:page>/<string:tags>/<string:ai>/<string:starred>/<string:converstion>', methods=['GET', 'POST'])
@check_and_validate_account
def filter_fetch(id, fetch, tags="", page=0, limit=25, ai="0", starred="0", conversation="0"):

    if ai == "1" or ai == "True":
        ai = True
    else:
        ai = False

    if starred == '1':
        starred = True
    else:
        starred = False

    if conversation == '1':
        conversation = True
    else:
        conversation = False

    if tags == "null":
        tags = ""

    try:
        if len(tags.strip()) > 0:
            if tags == "-1":
                tags = ""
            else:
                tags = tags.split(",")

        filter = {}
        options = {}

        highscore = False
        unparsed = False

        sortby = None
        sortorder = None
        
        is_read = False
        is_unread = False
        is_note_added = False

        if request.method == 'POST':
            
            if "filter" in request.json:
                filter = request.json['filter']
                logger.info("filter %s", filter)

            if "sort" in request.json:
                sort = request.json["sort"]

                if "sortby" in sort and "sortorder" in sort:
                    sortby = sort["sortby"]
                    sortorder = sort["sortorder"]

                else:
                    return jsonify({"sortby and order are missing"}), 200

            if "options" in request.json:
                options = request.json["options"]

                if "starred" in options:
                    starred = True

                if "conversation" in options:
                    conversation = True

                if "highscore" in options:
                    highscore = True

                if "unparsed" in options:
                    unparsed = True
                
                if 'is_read' in options:
                    is_read = True

                if 'is_unread' in options:
                    is_unread = True
                
                if 'is_note_added' in options:
                    is_note_added = True

        try:
            ret = sendFilterMessage({
                "id": id,
                "fetch": fetch,
                "page": page,
                "limit": limit,
                "tags": tags,
                "action": "fetch",
                "filter": filter,
                "ai": ai,
                "sortby": sortby,
                "sortorder": sortorder,
                "starred": starred,
                "conversation": conversation,
                "highscore": highscore,
                "unparsed": unparsed,
                "is_read" : is_read,
                "is_unread" : is_unread,
                "is_note_added" : is_note_added,
                "account_name": request.account_name,
                "account_config": request.account_config
            })
        except Exception as e:
            time.sleep(1)
            ret = sendFilterMessage({
                "id": id,
                "fetch": fetch,
                "page": page,
                "limit": limit,
                "tags": tags,
                "action": "fetch",
                "filter": filter,
                "ai": ai,
                "sortby": sortby,
                "sortorder": sortorder,
                "starred": starred,
                "conversation": conversation,
                "highscore": highscore,
                "unparsed": unparsed,
                "account_name": request.account_name,
                "account_config": request.account_config
            })

        return jsonify(ret), 200

    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/bulk/candidate', methods=['POST'])
@check_and_validate_account
def candidate_bulk():
    logger.info("sync bulk candidates")
    if request.method == 'POST':
        data = request.json['data']
        operation = data["operation"]

        if operation == "DELETE":
            candidate_ids = data["candidate_ids"]
            job_profile_id = data["job_profile_id"]

            sendMessage({
                "candidate_ids": candidate_ids,
                "action": "buld_delete",
                "job_profile_id": job_profile_id,
                "cur_time": time.time(),
                "account_name": request.account_name,
                "account_config": request.account_config,
                "priority": 10
            })

            return jsonify(""), 200

        elif operation == "ADD":
            docs = data["candidates"]
            job_profile_id = data["job_profile_id"]

            sendMessage({
                "docs": docs,
                "action": "bulk_add",
                "job_profile_id": job_profile_id,
                "cur_time": time.time(),
                "account_name": request.account_name,
                "account_config": request.account_config,
                "priority": 10
            })
            return jsonify(""), 200

        elif operation == "UPDATE":
            candidates = data["candidates"]
            job_profile_id = data["job_profile_id"]

            sendMessage({
                "candidates": candidates,
                "action": "bulk_update",
                "job_profile_id": job_profile_id,
                "cur_time": time.time(),
                "account_name": request.account_name,
                "account_config": request.account_config,
                "priority": 10
            })
            return jsonify(""), 200

        else:
            return jsonify("invalid operation"), 500

    else:
        return jsonify("invalid operation"), 500


@bp.route('/candidate/<string:id>', methods=['GET'])
@bp.route('/candidate/<string:id>/<string:field>', methods=['POST'])
@check_and_validate_account
def candidate(id, field=""):
    logger.info("got candidate %s", id)

    try:

        if request.method == 'POST':
            doc = request.json['data']
            logger.info("full doc %s", doc)

        sendMessage({
            "id": id,
            "field": field,
            "doc": doc,
            "action": "syncCandidate",
            "cur_time": time.time(),
            "account_name": request.account_name,
            "account_config": request.account_config,
            "priority": 10
        })

        return jsonify([]), 200

    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/classify-moved/<string:id>/<string:from_id>/<string:to_id>', methods=['GET'])
@check_and_validate_account
def classifyMoved(candidate_id, from_id, to_id):
    logger.info("got job profile from %s", from_id)
    logger.info("got job profile to %s", to_id)

    try:

        sendMessage({
            "candidate_id": candidate_id,
            "from_id": from_id,
            "to_id": to_id,
            "action": "classifyMoved",
            "cur_time": time.time(),
            "account_name": request.account_name,
            "account_config": request.account_config,
            "priority": 10
        })

        return jsonify([]), 200

    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/classify-job-moved/<string:candidate_id>/<string:from_classify_id>/<string:to_job_id>', methods=['GET'])
@check_and_validate_account
def classifyJobMoved(candidate_id, from_classify_id, to_job_id):
    logger.info("got job profile from %s", from_classify_id)
    logger.info("got job profile to %s", to_job_id)

    try:

        sendMessage({
            "candidate_id": candidate_id,
            "from_classify_id": from_classify_id,
            "to_job_id": to_job_id,
            "action": "classifyJobMoved",
            "cur_time": time.time(),
            "account_name": request.account_name,
            "account_config": request.account_config,
            "priority": 10
        })

        return jsonify([]), 200

    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/job-profile-moved/<string:candidate_id>/<string:from_id>/<string:to_id>', methods=['GET'])
@check_and_validate_account
def jobprofileMoved(candidate_id, from_id, to_id):
    logger.info("got job profile from %s", from_id)
    logger.info("got job profile to %s", to_id)

    try:

        sendMessage({
            "candidate_id": candidate_id,
            "from_id": from_id,
            "to_id": to_id,
            "action": "syncJobProfileChange",
            "cur_time": time.time(),
            "account_name": request.account_name,
            "account_config": request.account_config,
            "priority": 10
        })

        return jsonify([]), 200

    except Exception as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/job-profile/<string:id>', methods=['GET'])
@check_and_validate_account
def jobprofile(id):
    logger.info("got job profile id %s", id)

    try:

        sendMessage({
            "id": id,
            "action": "syncJobProfile",
            "cur_time": time.time(),
            "account_name": request.account_name,
            "account_config": request.account_config,
            "priority": 10
        })

        return jsonify([]), 200

    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/full', methods=['GET'])
@check_and_validate_account
def full():

    try:

        print(request.account_config)
        sendMessage({
            "action": "full",
            "cur_time": time.time(),
            "account_name": request.account_name,
            "account_config": request.account_config,
            "priority": 10
        })

        return jsonify([]), 200

    except KeyError as e:
        logger.critical(e)
        return jsonify(str(e)), 500


@bp.route('/filter/fix_name_email_phone_all', methods=['GET'])
@check_and_validate_account
def fix_name_email_phone_all():
    filterindex({
        "action": "fix_name_email_phone_all",
        "account_name": request.account_name,
        "account_config": request.account_config
    })

    return jsonify({}), 200
