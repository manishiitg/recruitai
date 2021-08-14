# problem is discussed on process_old.py
# solution
# a) make datasync more faster by mainly not caching the entire data. rather not cache data at all here, just delete the cache on datasync
# b) cache will be create on filtermq where we fetch data from mongodb. data will be mongo first and from mongo it will go to cache
# c) filters will be api based and again mongo first and then cache

import os
from threading import Thread, Lock

from app.publishsearch import sendMessage
from app.publishfilter import sendBlockingMessage as updateFilter
from app.publishresume import sendMessage as sendResumeMessage

from pymongo import MongoClient
from bson.objectid import ObjectId

from app.logging import logger
import json
import os
from bson import json_util


import traceback
import time
import datetime

from app.account import initDB
from app.account import connect_redis, r_set, r_exists, r_get, r_scan_iter, r_flushdb
from app.account import get_queues, get_resume_priority

def moveKey(candidate_id, from_key, to_key, account_name, account_config):

    if "undefined" in from_key or "undefined" in to_key:
        return 

    logger.critical(" from key %s", from_key)
    logger.critical(" to key %s", to_key)


    r = connect_redis(account_name, account_config)

    r_set("job_fx_"  + from_key, json.dumps(False), account_name, account_config)
    r_set("job_fx_"  + to_key, json.dumps(False), account_name, account_config)
    addFilter({
        "id" : from_key,
        "fetch" : "job_profile",
        "action" : "index",
        "account_name" : account_name,
        "account_config" : account_config
    }, from_key, account_name, account_config , True)

    addFilter({
        "id" : to_key,
        "fetch" : "job_profile",
        "action" : "index",
        "account_name" : account_name,
        "account_config" : account_config
    }, to_key, account_name, account_config , True)


def classifyMoved(candidate_id, from_id, to_id, account_name, account_config):
    moveKey(candidate_id, "classify_" + from_id, "classify_" + to_id, account_name, account_config)

def syncJobProfileChange(candidate_id, from_id, to_id, account_name, account_config):
    moveKey(candidate_id, "job_" + from_id, "job_" + to_id, account_name, account_config)

def classifyJobMoved(candidate_id, from_classify_id, to_job_id, account_name, account_config):
    moveKey(candidate_id, "classify_" + from_classify_id, "job_" + to_job_id, account_name, account_config)

def bulkDelete(candidate_ids, job_profile_id, account_name, account_config):
    r = connect_redis(account_name, account_config)
    r_set("job_fx_"  + job_profile_id, json.dumps(False), account_name, account_config)
    addFilter({
        "id" : job_profile_id,
        "fetch" : "job_profile",
        "action" : "index",
        "account_name" : account_name,
        "account_config" : account_config
    }, job_profile_id, account_name, account_config , True)


def bulkUpdate(candidates, job_profile_id, account_name, account_config):
    r = connect_redis(account_name, account_config)
    r_set("job_fx_"  + job_profile_id, json.dumps(False), account_name, account_config)
    addFilter({
        "id" : job_profile_id,
        "fetch" : "job_profile",
        "action" : "index",
        "account_name" : account_name,
        "account_config" : account_config
    }, job_profile_id, account_name, account_config , True)



def bulkAdd(docs, job_profile_id, account_name, account_config):

    r = connect_redis(account_name, account_config)
    r_set("job_fx_"  + job_profile_id, json.dumps(False), account_name, account_config)
    addFilter({
        "id" : job_profile_id,
        "fetch" : "job_profile",
        "action" : "index",
        "account_name" : account_name,
        "account_config" : account_config
    }, job_profile_id, account_name, account_config , True)


# recentProcessList = {}

from apscheduler.schedulers.background import BackgroundScheduler

import logging
log = logging.getLogger('apscheduler.executors.default')
log.setLevel(logging.CRITICAL)  # DEBUG


import copy

dirtyMap = {}
account_config_map = {}

is_queue_process_running = False
queue_running_count = 0
last_queue_process = 0
skip_count = 0



def check_and_send_for_ai(ret,job_criteria_map, db, account_name, account_config, is_fast_ai = False):
    count = 0
    actual_count = 0
    for row in ret:
        actual_count += 1
        logger.critical("checking %s", str(row["_id"]))
        
        if "email_timestamp" not in row:
            logger.critical("no timestamp found skipping %s", str(row["_id"]))
            continue
        
        if not is_fast_ai:
            if (time.time() - int(row["email_timestamp"]) / 1000) < 60 * 60 * 1:
                logger.critical("time stamp to early skipping %s", str(row["_id"]))
                continue

        

        logger.critical("found candidate %s", row["_id"])
        if "attachment" in row:
            if len(row["attachment"]) > 0:
                if "attachment" in row["attachment"][0]:
                    if "publicFolder" in row["attachment"][0]["attachment"]:
                        mongoid = str(row["_id"])
                        filename = row["attachment"][0]["attachment"]["publicFolder"]

                        meta = {
                            "filename": filename,
                            "mongoid": mongoid,
                            "cv_timestamp_seconds": int(row["email_timestamp"]) / 1000
                        }
                        if "job_profile_id" in row:
                            if len(row["job_profile_id"]) > 0:
                                job_profile_id = row["job_profile_id"]

                                if job_profile_id in job_criteria_map:

                                    if "skills" in job_criteria_map[job_profile_id]:
                                        skills = job_criteria_map[job_profile_id]["skills"]
                                    else:
                                        skills = []
                                    
                                    meta["criteria"] = job_criteria_map[job_profile_id]["criteria"]
                                else:
                                    skills = []
                                    meta["criteria"] = {}

                                
                            else:
                                skills = []

                        else:
                            skills = []

                        priority, days, cur_time = get_resume_priority(int(row["email_timestamp"]))
                        if is_fast_ai:
                            priority = 8

                        logger.critical("sending to ai parsing %s with priority %s", row["_id"], priority)
                        sendResumeMessage({
                            "filename" : filename,
                            "mongoid" : mongoid,
                            "skills" : skills,
                            "meta" : meta,
                            "priority" : priority,
                            "account_name": account_name,
                            "account_config" : account_config
                        })
                        count += 1
                    else:
                        logger.critical("attachment not proper for id %s", row["_id"])
                else:
                    logger.critical("attachment not proper for id %s", row["_id"])

        if not is_fast_ai:
            db.emailStored.update_one({
                "_id" : row["_id"]
            }, {
                "$set" : {
                    "check_ai_missing_data" : True
                }
            })
        else:
            db.emailStored.update_one({
                "_id" : row["_id"]
            }, {
                "$set" : {
                    "check_ai_fast_ai_2" : True
                }
            })

    logger.critical("total data count %s", actual_count)
    return count

def check_ai_missing_data(account_name, account_config):
    # need to check here if queue is empty first else this will cause problem
    # return {}
    try:
        queues = get_queues()
    except Exception as e:
        logger.critical(e)
        return
    
    in_process = queues["resume"]["in_process"] + queues["qa_full"]["in_process"]
    logger.critical("resume in progress %s", in_process)

    if in_process > 10:
        logger.critical("skipping checking ai missing data as resume in progress")
        return

    logger.critical("checking ai missing data")
    # some time randomly. few cv's are missing ai data. so checking them here and adding them ai data

    db = initDB(account_name, account_config)
    ret = db.emailStored.find({
            "$or" : [
                {"cvParsedAI" : { "$exists" : False }},
                {"cvParsedInfo.error" : { "$exists" : True }},
            ], 
            'check_ai_missing_data' : { "$exists" : False }
            # "attachment" : {  }
        },
        {"body": 0, "cvParsedInfo.debug": 0}
    )

    job_profile_rows = db.jobprofiles.find({
        "active_status": True
    }) 

    job_criteria_map = {}
    for job_profile_row in job_profile_rows:
        criteria = None
        if "criteria" in job_profile_row:
            criteria = job_profile_row["criteria"]
            if criteria is None:
                continue

            if "requiredFormat" in criteria:
                continue
            
            findSkills = []

            if "skills" in criteria:
                for value in criteria['skills']["values"]:
                    findSkills.append(value["value"])

        job_criteria_map[str(job_profile_row["_id"])] = {
            "criteria" : criteria,
            "skills" : findSkills
        }

    
    count = check_and_send_for_ai(ret,job_criteria_map, db, account_name, account_config)
    logger.critical("process missing ai %s", count)

    reduce_priority  = 0
    if "reduce_priority" in account_config:
        reduce_priority = int(account_config["reduce_priority"])
        

    if count == 0:
        logger.critical("checking for slow parsing, as cpu is empty can utilize it more")
        if reduce_priority >= 5:
            logger.critical("not checking due to low priority %s", reduce_priority)
            return 
            
        ret = db.emailStored.find({
                
                "$or": [
                    {"cvParsedInfo.qa_type" : {"$ne" : "full"}},
                    {"cvParsedInfo.qa_type" : {"$exists" : False}},
                ],
                "email_date" : { "$gt" : datetime.datetime.now() - datetime.timedelta(days=30) },
                'check_ai_fast_ai_2' : { "$exists" : False }
                # "attachment" : {  }
            },
            {"body": 0, "cvParsedInfo.debug": 0}
        ).sort("email_date", -1).limit(30)
        check_and_send_for_ai(ret,job_criteria_map, db, account_name, account_config, True)
    pass

# checkin_score_scheduler = BackgroundScheduler()
# checkin_score_scheduler.add_job(queue_process, trigger='interval', seconds=1*60 * 1) 
# 1min because now we are only updating files with this 

#*2.5
# checkin_score_scheduler.add_job(check_ai_missing_data, trigger='interval', seconds=60 * 60) 
# this will be called from frontend as we don't have db information etc without frontend.
# now this will process only filter only not actual redis data

# checkin_score_scheduler.start()





pastInfoMap = {}
redisKeyMap = {}

def init_maps(dirtyMap, redisKeyMap, account_config_map, account_name, account_config):
    account_config = account_config

    r = connect_redis(account_name, account_config)

    if account_name not in dirtyMap:
        dirtyMap[account_name] = {}

    if account_name not in pastInfoMap:
        pastInfoMap[account_name] = {}

    if account_name not in redisKeyMap:
        redisKeyMap[account_name] = {}
        logger.critical("loading redis key map for account %s " % account_name)
        for key in r_scan_iter(account_name, account_config):
            if "job_" in key or "classify_" in key:
                logger.critical("loading key %s", key)
                redisKeyMap[account_name][key] = json.loads(r_get(key, account_name, account_config))

        logger.critical("loaded redis key map")

    return dirtyMap, redisKeyMap, account_config_map


def process(findtype = "full", cur_time = None, mongoid = "", field = None, doc = None, account_name = None, account_config = {}):
    if account_name is None:
        logger.critical("account name not found")
        return 

    global dirtyMap
    global redisKeyMap
    global pastInfoMap
    global account_config_map
    global is_queue_process_running
    global queue_running_count
        
        
    is_queue_process_running = True


    # if account_name == "devrecruit":
    #     # this is temporary need to fix mongo issues for live server
    #     logger.critical("skipping account %s", account_name)
    #     return

    r = connect_redis(account_name, account_config)
    local_dirtyMap = {}
    local_dirtyMap, redisKeyMap, account_config_map = init_maps(dirtyMap, redisKeyMap, account_config_map, account_name, account_config)


    

    threads = []

    if cur_time is None:
        cur_time = time.time()


    isFilterUpdateNeeded = False
    logger.critical(account_config)
    db = initDB(account_name, account_config)
    if findtype == "syncCandidate":
        # allowedfields = ['unread', 'job_profile_id', 'tag_id', 'notes', 'candidate_star', 'callingStatus' ]


        logger.critical("field which got updated %s", field)
        if field is not None:
            if "tag_id" in field or 'job_profile_id' in field or 'is_archieved' in field or "sequence" in field or "ex_job_profile":
                isFilterUpdateNeeded = True


        logger.critical("syncCandidate")

        if not isFilterUpdateNeeded:
            logger.critical("filters not getting updated ")
        else:
            logger.critical("filters getting updated ")

        

        if doc is None:
            logger.critical("not doc found not good!")
            start_time = time.time()
            if ObjectId.is_valid(mongoid):
                ret = db.emailStored.find({ 
                    "_id" : ObjectId(mongoid),
                    } , 
                    {"body": 0, "cvParsedInfo.debug": 0}
                )

                logger.critical("time to fetch docs %s", time.time() - start_time)
            else:
                ret = []
            # .sort([("sequence", -1),("updatedAt", -1)])
            # sort gives ram error
        else:
            ret = [doc]
        

        if not isFilterUpdateNeeded and doc:
            # need to update secondary caching still
            print("updating unique cache ")
            
            if "tag_id" not in doc:
                doc["tag_id"] = ""

    elif findtype == "syncJobProfile":
        logger.critical("syncJobProfile")
        job_profile_id = mongoid


        logger.critical("cur time %s", cur_time)
        isFilterUpdateNeeded = True
        
        ret = db.emailStored.find({ 
            "job_profile_id" : mongoid,
            # "cvParsedInfo.debug" : {"$exists" : True} 
            } , 
        {"body": 0, "cvParsedInfo.debug": 0}
        )
        # .sort([("sequence", -1),("updatedAt", -1)])
        # .sort([("sequence", -1),("updatedAt", -1)])
            # sort gives ram error

        r_set("job_fx_"  + job_profile_id, json.dumps(False), account_name, account_config)
        addFilter({
            "id" : job_profile_id,
            "fetch" : "job_profile",
            "action" : "index",
            "account_name" : account_name,
            "account_config" : account_config
        }, job_profile_id, account_name, account_config , True)

    elif findtype == "full":
        logger.critical("full")

        if "full" in pastInfoMap[account_name]:
            t = pastInfoMap[account_name]["full"]

            if t > cur_time:
                logger.critical("skipping the sync as we have already synced more recent data")
                is_queue_process_running =  False
                return ""

            logger.critical("full sync past time %s and current time %s difference %s", t, cur_time, (cur_time - t))
            if abs(time.time() - t) < 60 * 60 * 1:
                logger.critical("skipping the sync as we have already synced more recent data")
                is_queue_process_running =  False
                return ""

        pastInfoMap[account_name]["full"] = time.time()

        r_flushdb(account_name, account_config)
        redisKeyMap[account_name] = {}
        local_dirtyMap[account_name] = {}
        
        data = []
        ret = db.emailStored.find({ } , 
            {"body": 0, "cvParsedInfo.debug": 0}
        )
        for row in ret:
            data.append(row)
            # pymongo.errors.CursorNotFound: cursor id 7596185392783291209 not found, full error: {'ok': 0.0, 'errmsg': 'cursor id 7596185392783291209 not found', 'code': 43, 'codeName': 'CursorNotFound'}

        for row in data:
            row["_id"] = str(row["_id"])   
            sendToSearchIndex(row , r, "full", account_name, account_config)
            job_profile_id = None

            if "job_profile_id" in row:
                if len(row['job_profile_id']) > 0:
                    job_profile_id = row['job_profile_id']

            if job_profile_id not in redisKeyMap[account_name]:
                redisKeyMap[account_name][job_profile_id] = {}

            redisKeyMap[account_name][job_profile_id][str(row["_id"])] = row

        isFilterUpdateNeeded = True

        # .sort([("sequence", -1),("updatedAt", -1)])
        # .sort([("sequence", -1),("updatedAt", -1)])
            # sort gives ram error
    else:
        ret = []
        logger.critical("should not be here88888888888888888888888888888888888888888888888")
    

    if findtype == "syncCandidate" or findtype == "syncJobProfile":
        for row in ret:
            if isinstance(row, float):
                logger.critical("again float")
                continue

            row["_id"] = str(row["_id"])            

            job_profile_id  = None

            print(row.keys())
            if "job_profile_id" in row:
                if len(row["job_profile_id"]) > 0:
                    job_profile_id = row["job_profile_id"]
            
            

                
            sendToSearchIndex(row, r, findtype, account_name, account_config)
            logger.critical("job profile %s", job_profile_id)
            if job_profile_id is not None:
                
                
                r_set("job_fx_"  + job_profile_id, json.dumps(False), account_name, account_config)

                if isFilterUpdateNeeded:
                    addFilter({
                        "id" : job_profile_id,
                        "fetch" : "job_profile",
                        "action" : "index",
                        "account_name" : account_name,
                        "account_config" : account_config
                    }, job_profile_id, account_name, account_config , True)


                if job_profile_id not in redisKeyMap[account_name]:
                    redisKeyMap[account_name][job_profile_id] = {}

                redisKeyMap[account_name][job_profile_id][str(row["_id"])] = row

                if "is_archieved" in row.keys():
                    # above automatically takes care of it 
                    pass
            else:
                # when we remove candidate from job profile id, then job_profile_id is not there in json
                job_map = redisKeyMap[account_name]
                
                
                for key in job_map:
                    if not key:
                        continue
                    
                    if "job_" in key:
                        if isinstance(job_map[key], dict):
                            if row["_id"] in job_map[key]:
                                job_profile_data = job_map[key]
                                del job_profile_data[row["_id"]]
                                redisKeyMap[account_name][key] = job_profile_data
                                r_set("job_fx_"  + key, json.dumps(False), account_name, account_config)
                                if isFilterUpdateNeeded:
                                    addFilter({
                                        "id" : key,
                                        "fetch" : "job_profile",
                                        "action" : "index",
                                        "account_name" : account_name,
                                        "account_config" : account_config
                                    }, key, account_name, account_config , True)

                                logger.critical("candidate removed from job deleted %s", row["_id"])
                                break

                job_profile_id = None

                if "ex_job_profile" not in row:
                    mapKey = "classify_NOT_ASSIGNED"
                    is_old = False
                    month_year = ""
                    days = 0

                    if "email_timestamp" in row:
                        timestamp_seconds = int(row["email_timestamp"])/1000
                        month_year = "-" +  datetime.datetime.fromtimestamp(timestamp_seconds).strftime('%Y-%b')

                        cur_time = time.time()
                        days =  abs(cur_time - timestamp_seconds)  / (60 * 60 * 24 )

                        if days < 15:
                            is_old = False
                        else:
                            is_old = True

                    else:
                        is_old = False
                    
                    if is_old:
                        mapKey = "classify_NOT_ASSIGNED" + month_year

                    r_set("classify_fx_"  + mapKey, json.dumps(False), account_name, account_config)
                    if isFilterUpdateNeeded:
                        addFilter({
                            "id" : mapKey.replace("classify_",""),
                            "fetch" : "candidate",
                            "action" : "index",
                            "account_name" : account_name,
                            "account_config" : account_config
                        }, mapKey.replace("classify_",""), account_name, account_config , True)

                
            
            
            if "ex_job_profile" in row:
                if row["ex_job_profile"] and "name" in row["ex_job_profile"]:
                    candidate_label = "Ex:" + row["ex_job_profile"]["name"]
                    mapKey = "classify_" + candidate_label
                    days = 0
                    if "email_timestamp" in row:
                        timestamp_seconds = int(row["email_timestamp"])/1000
                        month_year = "-" +  datetime.datetime.fromtimestamp(timestamp_seconds).strftime('%Y-%b')

                        cur_time = time.time()
                        days =  abs(cur_time - timestamp_seconds)  / (60 * 60 * 24 )

                        if days > 15:
                            mapKey = mapKey + month_year

                    r_set("classify_fx_"  + mapKey, json.dumps(False), account_name, account_config)
                    if isFilterUpdateNeeded:
                        addFilter({
                            "id" : mapKey.replace("classify_",""),
                            "fetch" : "candidate",
                            "action" : "index",
                            "account_name" : account_name,
                            "account_config" : account_config
                        }, mapKey.replace("classify_",""), account_name, account_config , True)

                    if candidate_label is not None:
                        logger.critical("candidate labels %s", candidate_label)
                        mapKey = "classify_" + candidate_label
                        days = 0

                        if "email_timestamp" in row:
                            timestamp_seconds = int(row["email_timestamp"])/1000
                            month_year = "-" +  datetime.datetime.fromtimestamp(timestamp_seconds).strftime('%Y-%b')

                            cur_time = time.time()
                            days =  abs(cur_time - timestamp_seconds)  / (60 * 60 * 24 )
                            if days > 15:
                                mapKey = mapKey + month_year

                        r_set("classify_fx_"  + mapKey, json.dumps(False), account_name, account_config)
                        if isFilterUpdateNeeded:
                            addFilter({
                                "id" : mapKey.replace("classify_",""),
                                "fetch" : "candidate",
                                "action" : "index",
                                "account_name" : account_name,
                                "account_config" : account_config
                            }, mapKey.replace("classify_",""), account_name, account_config , True)


        
        
    is_queue_process_running =  False
    logger.critical("######### process completed")
        
    


time_map = {}

def sendToSearchIndex(row, r, from_type, account_name, account_config):
    if from_type == "full":
    # this gets slow with full when data is large
        return

    row["_id"] = str(row["_id"])
    finalLines = []
    if "cvParsedInfo" in row:
        cvParsedInfo = row["cvParsedInfo"]
        if "newCompressedStructuredContent" in cvParsedInfo:
            for page in cvParsedInfo["newCompressedStructuredContent"]:
                for pagerow in cvParsedInfo["newCompressedStructuredContent"][page]:
                    if len(pagerow["line"]) > 0:
                        finalLines.append(pagerow["line"])
    
    if "subject" not in row:
        row["subject"] = ""
    
    if "sender_mail" not in row:
        row["sender_mail"] = ""

    if "from" not in row:
        row["from"] = ""

    
    finalLines.append(row["subject"])
    finalLines.append(row["from"])
    finalLines.append(row["sender_mail"])
    
    if len(finalLines) > 0:
        
        if not r_exists("search_ " + row['_id'], account_name, account_config):
            logger.critical("add to search %s", account_name)
            # if key exists in redis, this means before search was already indexed. the content doesn't change at all much
            # this is causing on redis level also, but if don't add this. elastic seach also get loaded a lot which is a problem. 
            # so need to add this and fix redis issue
            t = Thread(target=addToSearch, args=(row["_id"],finalLines,{}, account_name, account_config))
            t.start()
            r_set("search_" + row["_id"], "1", account_name, account_config, ex= 1 * 60 * 60)
        else:
            logger.critical("skipped add to search")

def addFilter(obj, key, account_name, account_config, is_direct):
    global dirtyMap
    global time_map
    ignore = False
    # this will be done on frontend now.
    # this is a time taking operation and used very very less. 
    return 
    # if obj["action"] == "index":
    #     if obj["fetch"] not in time_map:
    #         time_map[obj["fetch"]] = {}

    #     id = obj["id"]
    #     if id not in time_map[obj["fetch"]]:
    #         time_map[obj["fetch"]][id] = time.time()
    #         logger.critical("added new fetch %s", id)
    #         ignore = True
    #         dirtyMap[account_name][key] = {
    #             "filter_dirty" : True,
    #             "redis_dirty" : False # True it was true before
    #         }
    #     else:
    #         ctime = time_map[obj["fetch"]][id]
    #         logger.critical("time for add Filter %s",  time.time() - ctime )
    #         if (time.time() - ctime) < 1 * 60 or is_direct:
    #             ignore = True
    #             dirtyMap[account_name][key] = {
    #                 "filter_dirty" : True,
    #                 "redis_dirty" : False # True it was true before
    #             }
    #             # see we are setting directy map. this means it will again trigger for sure
    #             logger.critical("ignoreed %s" , obj)
    #         else:
    #             time_map[obj["fetch"]][id] = time.time()
    # else:
    #     logger.critical("different action found %s", obj)


    # if not ignore:
    try:
        # Thread(target=updateFilter, args=( obj , )).start() giving errors. 
        logger.critical("sending to filter mq %s" , obj)
        ret = updateFilter(obj)
        logger.critical("receieved from filter %s" , ret)
    except Exception as e:
            logger.critical(str(e))
            traceback.print_exc(e)
    # else:
    #     logger.critical("addfilter skipped")

def addToSearch(mongoid, finalLines, ret, account_name, account_config):
    try:
        sendMessage({
            "id": mongoid,
            "lines" : finalLines,
            "extra_data" : ret,
            "action" : "addDoc",
            "account_name" : account_name,
            "account_config" : account_config
        })
    except Exception as e:
        logger.critical(str(e))
        traceback.print_exc(e)
