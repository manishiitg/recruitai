import os
from threading import Thread

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

from app.account import initDB
from app.account import connect_redis

def moveKey(candidate_id, from_key, to_key, account_name, account_config):

    global redisKeyMap
    global dirtyMap
    global account_config_map

    dirtyMap, redisKeyMap, account_config_map = init_maps(dirtyMap, redisKeyMap, account_config_map, account_name, account_config)


    logger.critical(" from key %s", from_key)
    logger.critical(" to key %s", to_key)

    r = connect_redis(account_name, account_config)

    from_job_profile_data = redisKeyMap[account_name][from_key]
    if not from_job_profile_data:
        logger.critical("from not found some issue")
        return

    if to_key in redisKeyMap[account_name]:
        to_job_profile_data = redisKeyMap[account_name][to_key]
    else:
        to_job_profile_data = {}

    if not to_job_profile_data:
        to_job_profile_data = {}

    if candidate_id in from_job_profile_data:
        del from_job_profile_data[candidate_id]
        redisKeyMap[account_name][from_key] = from_job_profile_data

    dirtyMap[account_name][from_key] = {
        "filter_dirty" : True,
        "redis_dirty" : True
    }
    
    db = initDB(account_name, account_config)
    row = db.emailStored.find_one({ 
            "_id" : ObjectId(candidate_id) } , 
            {"body": 0, "cvParsedInfo.debug": 0}
        )
        # .sort([("sequence", -1),("updatedAt", -1)])
            # sort gives ram error
    if row:
        to_job_profile_data[candidate_id] = row
        redisKeyMap[account_name][to_key] = to_job_profile_data
        dirtyMap[account_name][to_key] = {
            "filter_dirty" : True,
            "redis_dirty" : True
        }
        # r.set(candidate_id  , json.dumps(row,default=json_util.default))


    # r.set(from_key  , json.dumps(from_job_profile_data , default=json_util.default))
    # r.set(to_key  , json.dumps(to_job_profile_data , default=json_util.default))
    queue_process(True)

def classifyMoved(candidate_id, from_id, to_id, account_name, account_config):
    moveKey(candidate_id, "classify_" + from_id, "classify_" + to_id, account_name, account_config)

def syncJobProfileChange(candidate_id, from_id, to_id, account_name, account_config):
    moveKey(candidate_id, "job_" + from_id, "job_" + to_id, account_name, account_config)

def classifyJobMoved(candidate_id, from_classify_id, to_job_id, account_name, account_config):
    moveKey(candidate_id, "classify_" + from_classify_id, "job_" + to_job_id, account_name, account_config)

def bulkDelete(candidate_ids, job_profile_id, account_name, account_config):

    global dirtyMap
    global redisKeyMap
    global account_config_map

    r = connect_redis(account_name, account_config)

    dirtyMap, redisKeyMap, account_config_map = init_maps(dirtyMap, redisKeyMap, account_config_map, account_name, account_config)

    logger.critical("job profile %s", job_profile_id)
    mapKey = "job_" + job_profile_id
    if mapKey not in redisKeyMap[account_name]:
        job_profile_data = r.get(mapKey)
        if job_profile_data:
            job_profile_data = json.loads(job_profile_data)
        else:
            job_profile_data = {}
    else:
        job_profile_data = redisKeyMap[account_name][mapKey]

    for candidate_id in candidate_ids:
        del job_profile_data[candidate_id]

    redisKeyMap[account_name][mapKey] = job_profile_data

    dirtyMap[account_name][mapKey] = {
        "filter_dirty" : True,
        "redis_dirty" : True
    }
    queue_process(True)

def bulkUpdate(candidates, job_profile_id, account_name, account_config):
    global dirtyMap
    global redisKeyMap
    global account_config_map

    r = connect_redis(account_name, account_config)

    dirtyMap, redisKeyMap, account_config_map = init_maps(dirtyMap, redisKeyMap, account_config_map, account_name, account_config)

    logger.critical("bulk field update profile %s", job_profile_id)

    logger.critical("bulk add job profile %s", job_profile_id)
    if isinstance(job_profile_id, list):
        job_profile_id = job_profile_id[0]
        
    mapKey = "job_" + job_profile_id
    if mapKey not in redisKeyMap[account_name]:
        job_profile_data = r.get(mapKey)
        if job_profile_data:
            job_profile_data = json.loads(job_profile_data)
        else:
            job_profile_data = {}
    else:
        job_profile_data = redisKeyMap[account_name][mapKey]

    for row in candidates:
        row["_id"] = str(row["_id"])
        

        if "job_profile_id" not in row or not row["job_profile_id"]:
            if row["_id"] in job_profile_data:
                del job_profile_data[row["_id"]]
        else:
            job_profile_data[row["_id"]] = row
            
        r.set(row["_id"]  , json.dumps(row,default=json_util.default))

        candidate_label = None
        if "candidateClassify" in row:
            if "label" in row["candidateClassify"]:
                candidate_label = row["candidateClassify"]["label"]
                if str(candidate_label) == "False":
                    candidate_label = None

        if candidate_label is not None:
            logger.critical("candidate labels %s", candidate_label)
            mapKey2 = "classify_" + candidate_label
            if mapKey2 not in redisKeyMap[account_name]:
                candidate_data = r.get(mapKey2)
                if candidate_data:
                    candidate_data = json.loads(candidate_data)
                else:
                    candidate_data = {}
            else:
                candidate_data = redisKeyMap[account_name][mapKey2]

            # if row["_id"] in candidate_data:
            candidate_data[row["_id"]] = row

            redisKeyMap[account_name][mapKey2] = candidate_data
            dirtyMap[account_name][mapKey2] = {
                "filter_dirty" : True,
                "redis_dirty" : True
            }

    redisKeyMap[account_name][mapKey] = job_profile_data
    dirtyMap[account_name][mapKey] = {
        "filter_dirty" : True,
        "redis_dirty" : True
    }
    queue_process(True)



def bulkAdd(docs, job_profile_id, account_name, account_config):

    global dirtyMap
    global redisKeyMap
    global account_config_map

    r = connect_redis(account_name, account_config)

    dirtyMap, redisKeyMap, account_config_map = init_maps(dirtyMap, redisKeyMap, account_config_map, account_name, account_config)

    logger.critical("bulk add job profile %s", job_profile_id)
    mapKey = "job_" + job_profile_id
    if mapKey not in redisKeyMap[account_name]:
        job_profile_data = r.get(mapKey)
        if job_profile_data:
            job_profile_data = json.loads(job_profile_data)
        else:
            job_profile_data = {}
    else:
        job_profile_data = redisKeyMap[account_name][mapKey]

    for row in docs:
        row["_id"] = str(row["_id"])
        job_profile_data[row["_id"]] = row
        r.set(row["_id"]  , json.dumps(row,default=json_util.default))

        candidate_label = None
        if "candidateClassify" in row:
            if "label" in row["candidateClassify"]:
                candidate_label = row["candidateClassify"]["label"]
                if str(candidate_label) == "False":
                    candidate_label = None

        if candidate_label is not None:
            logger.critical("candidate labels %s", candidate_label)
            mapKey2 = "classify_" + candidate_label
            if mapKey2 not in redisKeyMap[account_name]:
                candidate_data = r.get(mapKey2)
                if candidate_data:
                    candidate_data = json.loads(candidate_data)
                else:
                    candidate_data = {}
            else:
                candidate_data = redisKeyMap[account_name][mapKey2]

            # if row["_id"] in candidate_data:
            candidate_data[row["_id"]] = row

            redisKeyMap[account_name][mapKey2] = candidate_data
            dirtyMap[account_name][mapKey2] = {
                        "filter_dirty" : True,
                        "redis_dirty" : True
                    }

    redisKeyMap[account_name][mapKey] = job_profile_data
    dirtyMap[account_name][mapKey] = {
                        "filter_dirty" : True,
                        "redis_dirty" : True
                    }
    queue_process(True)

    
    


def bulkDelete(candidate_ids, job_profile_id, account_name, account_config):

    r = connect_redis(account_name, account_config)

    global dirtyMap
    global redisKeyMap
    global account_config_map
    
    dirtyMap, redisKeyMap, account_config_map = init_maps(dirtyMap, redisKeyMap, account_config_map, account_name, account_config)

    logger.critical("bulk delete job profile %s", job_profile_id)
    if ObjectId.is_valid(job_profile_id):
        mapKey = "job_" + job_profile_id
    else:
        mapKey = "classify_" + job_profile_id

    if mapKey not in redisKeyMap[account_name]:
        job_profile_data = r.get(mapKey)
        if job_profile_data:
            job_profile_data = json.loads(job_profile_data)
        else:
            job_profile_data = {}
    else:
        job_profile_data = redisKeyMap[account_name][mapKey]

    for candidate_id in candidate_ids:
        del job_profile_data[candidate_id]

    redisKeyMap[account_name][mapKey] = job_profile_data

    dirtyMap[account_name][mapKey] = {
                        "filter_dirty" : True,
                        "redis_dirty" : True
                    }
    queue_process(True)


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

def queue_process(is_direct = False):

    global dirtyMap
    global is_queue_process_running
    global queue_running_count

    queue_running_count += 1
    if queue_running_count < 20:
        if is_queue_process_running:
            logger.critical("queue is already running...")
            return

    is_queue_process_running = True

    localMap = dirtyMap
    # localMap = copy.deepcopy(dirtyMap)

    # for account_name in dirtyMap:
    #     dirtyMap[account_name] = {}
    # this is causing issues with long run process. like full sync. full is running but in between dirtyMap gets empty
    # so data is inconsistant

    logger.critical("checking dirty data %s" , localMap)
    for account_name in localMap:
        r = connect_redis(account_name, account_config_map[account_name])
        # print(localMap[account_name].keys())
        for key in localMap[account_name]:

            operations = localMap[account_name][key]
            if operations["redis_dirty"]:
                logger.critical("keyyyyyyyyyyyyyy %s", key)
                logger.critical("updating redis %s" , key)
                logger.critical("redis data len %s", len(redisKeyMap[account_name][key]))
                r.set(key, json.dumps(redisKeyMap[account_name][key], default=str))
                r.set(key + "_len", len(redisKeyMap[account_name][key]))
                r.set(key + "_time", time.time()) # we basically set a time when this redis was last updated. and use that in filtermq where we cache things
                logger.critical("updated redis %s" , key)

                if "classify_" in key:
                    if r.exists("classify_list"):
                        classify_list = r.get("classify_list")
                        classify_list = json.loads(classify_list)
                    else:
                        classify_list = []
                    
                    classify_list.append(key)
                    classify_list = list(set(classify_list))

                    # print("[pppppppppppppppppppppppppppppppppppppppppppppppppppppppppp")
                    # print(key)
                    # print(classify_list)
                    r.set("classify_list", json.dumps(classify_list))

                dirtyMap[account_name][key]["redis_dirty"] = False  
            if operations["filter_dirty"]:
                dirtyMap[account_name][key]["filter_dirty"] = False  
                if "job_" in key:
                    addFilter({
                            "id" : key.replace("job_",""),
                            "fetch" : "job_profile",
                            "action" : "index",
                            "account_name" : account_name,
                            "account_config" : account_config_map[account_name]
                        }, key, account_name, account_config_map[account_name] , is_direct)
                elif "classify_" in key:
                    addFilter({
                            "id" : key.replace("classify_",""),
                            "fetch" : "candidate",
                            "action" : "index",
                            "account_name" : account_name,
                            "account_config" : account_config_map[account_name]
                        }, key, account_name, account_config_map[account_name], is_direct)

                    
            # del dirtyMap[account_name][key]        

            logger.critical("job profile filter completed")

    logger.critical("#########################process queue completed")
    is_queue_process_running = False
    queue_running_count = 0
    

def check_ai_missing_data(account_name, account_config):

    # return {}
    logger.critical("checking ai missing data")
    # some time randomly. few cv's are missing ai data. so checking them here and adding them ai data

    logger.critical("check missing ai data")

    db = initDB(account_name, account_config)
    ret = db.emailStored.find({
            "$or" : [
                {"cvParsedAI" : { "$exists" : False }},
                {"cvParsedAI.error" : { "$exists" : False }},
            ], 
            'check_ai_missing_data' : { "$exists" : True }
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


    for row in ret:
        

        
        if "email_timestamp" not in row:
            continue
        
        if (time.time() - int(row["email_timestamp"]) / 1000) < 60 * 60 * 1:
            continue

        db.emailStored.update_one({
            "_id" : row["_id"]
        }, {
            "$set" : {
                "check_ai_missing_data" : True
            }
        })

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

                        priority = 5
                        logger.critical("sending to ai parsing %s", row["_id"])
                        sendResumeMessage({
                            "filename" : filename,
                            "mongoid" : mongoid,
                            "skills" : skills,
                            "meta" : meta,
                            "priority" : priority,
                            "account_name": account_name,
                            "account_config" : account_config
                        })
                    else:
                        logger.critical("attachment not proper for id %s", row["_id"])
                else:
                    logger.critical("attachment not proper for id %s", row["_id"])

    pass

checkin_score_scheduler = BackgroundScheduler()
checkin_score_scheduler.add_job(queue_process, trigger='interval', seconds=1*60 * 1) 
# 1min because now we are only updating files with this 

#*2.5
# checkin_score_scheduler.add_job(check_ai_missing_data, trigger='interval', seconds=60 * 60) 
# this will be called from frontend as we don't have db information etc without frontend.
# now this will process only filter only not actual redis data

checkin_score_scheduler.start()





pastInfoMap = {}
redisKeyMap = {}

def init_maps(dirtyMap, redisKeyMap, account_config_map, account_name, account_config):
    account_config_map[account_name] = account_config

    r = connect_redis(account_name, account_config)

    if account_name not in dirtyMap:
        dirtyMap[account_name] = {}

    if account_name not in pastInfoMap:
        pastInfoMap[account_name] = {}

    if account_name not in redisKeyMap:
        redisKeyMap[account_name] = {}
        logger.critical("loading redis key map for account %s " % account_name)
        for key in r.scan_iter():
            if "job_" in key or "classify_" in key:
                logger.critical("loading key %s", key)
                redisKeyMap[account_name][key] = json.loads(r.get(key))

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


    # if account_name != "devrecruit":
    #     # this is temporary need to fix mongo issues for live server
    #     logger.critical("skipping account %s", account_name)
    #     return

    r = connect_redis(account_name, account_config)
    local_dirtyMap = {}
    local_dirtyMap, redisKeyMap, account_config_map = init_maps(dirtyMap, redisKeyMap, account_config_map, account_name, account_config)


    

    threads = []

    if cur_time is None:
        cur_time = time.time()


    # "job_profile_id": mongoid

    # global recentProcessList

    # if findtype != "full":
    #     recentProcessList[mongoid+"-"+findtype] = time.time()


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


            r.set(doc['job_profile_id'] + "_time", time.time()) # we basically set a time when this redis was last updated. and use that in filtermq where we cache things

            # obj = {
            #     'tag_id' : doc["tag_id"],
            #     "job_profile_id" : doc['job_profile_id'],
            #     "action" : "update_unique_cache",
            #     "account_name" : account_name,
            #     "account_config": account_config
            # }
            # Thread(target=updateFilter, args=( obj , )).start()
            # 
            # updateFilter(obj)

    elif findtype == "syncJobProfile":
        logger.critical("syncJobProfile")
        job_profile_id = mongoid


        logger.critical("cur time %s", cur_time)
        if "syncJobProfile" + job_profile_id in pastInfoMap:
            t = pastInfoMap[account_name]["syncJobProfile" + job_profile_id]

            if t > cur_time:
                logger.critical("skpping the sync as we have already synced more recent data")
                return ""

        pastInfoMap[account_name]["syncJobProfile" + job_profile_id] = time.time()

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
    else:
        logger.critical("full")

        if "full" in pastInfoMap[account_name]:
            t = pastInfoMap[account_name]["full"]

            if t > cur_time:
                logger.critical("skpping the sync as we have already synced more recent data")
                return ""

        pastInfoMap[account_name]["full"] = time.time()

        # r.flushdb()
        # this is wrong. this remove much more data like resume parsed information etc
        redisKeyMap[account_name] = {}
        local_dirtyMap[account_name] = {}
        for key in r.scan_iter(): #this takes time
            if "classify_" in key or "job_" in key or "_filter" in key or "jb_" in key:
                logger.critical("delete from redis %s", key)
                r.delete(key)
                
        ret = db.emailStored.find({ } , 
            {"body": 0, "cvParsedInfo.debug": 0}
        )

        isFilterUpdateNeeded = True
        # .sort([("sequence", -1),("updatedAt", -1)])
        # .sort([("sequence", -1),("updatedAt", -1)])
            # sort gives ram error


    job_profile_map = {}
    candidate_map = {}

    full_map = {}

    for row in ret:
        if isinstance(row, float):
            logger.critical("again float")
            continue

        row["_id"] = str(row["_id"])

        if "cvParsedInfo" in row:
            cvParsedInfo = row["cvParsedInfo"]
            if "debug" in cvParsedInfo:
                del row["cvParsedInfo"]["debug"]

        # logger.critical(row["_id"])
        if "job_profile_id" in row and len(row["job_profile_id"]) > 0:
            job_profile_id = row["job_profile_id"]
        else:
            # logger.critical("job profile not found!!!")
            job_profile_id = None

            mapKey = "classify_NOT_ASSIGNED"

            if mapKey not in redisKeyMap[account_name]:
                job_data = r.get(mapKey)
                if job_data is None:
                    job_data = {}
                else:
                    job_data = json.loads(job_data)
            else:
                job_data = redisKeyMap[account_name][mapKey]
                
            job_data[row["_id"]] = row
            redisKeyMap[account_name][mapKey] = job_data

            local_dirtyMap[account_name][mapKey] = {
                "filter_dirty" : True,
                "redis_dirty" : True
            }
            
        

        

        finalLines = []
        if "cvParsedInfo" in row:
            cvParsedInfo = row["cvParsedInfo"]
            if "newCompressedStructuredContent" in cvParsedInfo:
                for page in cvParsedInfo["newCompressedStructuredContent"]:
                    for pagerow in cvParsedInfo["newCompressedStructuredContent"][page]:
                        if len(pagerow["line"]) > 0:
                            finalLines.append(pagerow["line"])

        candidate_label = None
        if "candidateClassify" in row:
            if "label" in row["candidateClassify"]:
                candidate_label = row["candidateClassify"]["label"]
                if str(candidate_label) == "False":
                    candidate_label = None
                if candidate_label:
                    if candidate_label not in candidate_map:
                        candidate_map[candidate_label] = {}

                    candidate_map[candidate_label][row["_id"]] = row

        if "ex_job_profile" in row:
            candidate_label = "Ex-" + row["ex_job_profile"]["name"]
            if candidate_label not in candidate_map:
                candidate_map[candidate_label] = {}
            candidate_map[candidate_label][row["_id"]] = row

            
        full_map[row["_id"]] = row
        if job_profile_id is not None:
            if job_profile_id not in job_profile_map:
                job_profile_map[job_profile_id] = {}

            job_profile_map[job_profile_id][row["_id"]] = row

        sendToSearchIndex(row , r, "full", account_name, account_config)
        
        r.set(row["_id"]  , json.dumps(row,default=json_util.default))

        if findtype == "syncCandidate" or findtype == "syncJobProfile":
            # if job_profile_id:
            #     job_profile_data_existing = r.get("job_" + job_profile_id)
            #     job_profile_data_now = json.dumps(row,default=json_util.default)

           

            # this is very very slow for full job profile 
            # need to add bulk to search or something

            # no need of tread or async way so that we can reuse connection for pika
            # if we use threads then many threads start even before connection is created 
            # so they create multiple connections
            # threads.append(t)
            sendToSearchIndex(row, r, findtype, account_name, account_config)
            
            if job_profile_id is not None:
                logger.critical("job profile %s", job_profile_id)
                mapKey = "job_" + job_profile_id
                if mapKey not in redisKeyMap[account_name]:
                    job_profile_data = r.get(mapKey)
                    

                    if job_profile_data:
                        job_profile_data = json.loads(job_profile_data)
                    else:
                        job_profile_data = {}
                else:
                    job_profile_data = redisKeyMap[account_name][mapKey]

                if isinstance(job_profile_data, list):
                    job_profile_data = {}

                # if row["_id"] in job_profile_data:
                if not row["job_profile_id"] or len(row["job_profile_id"]) == 0:
                    del job_profile_data[row["_id"]]
                else:
                    if "is_archieved" in row.keys():
                        if row["is_archieved"] == "true" or row["is_archieved"] == True:
                            if row["_id"] in job_profile_data:
                                del job_profile_data[row["_id"]]
                        else:
                            job_profile_data[row["_id"]] = row
                    else:
                        job_profile_data[row["_id"]] = row


                redisKeyMap[account_name][mapKey] = job_profile_data

                if isFilterUpdateNeeded: 
                    local_dirtyMap[account_name][mapKey] = {
                        "filter_dirty" : True,
                        "redis_dirty" : True
                    }
                else:
                    local_dirtyMap[account_name][mapKey] = {
                        "redis_dirty" : True,
                        "filter_dirty" : False
                    }
            else:
                # when we remove candidate from job profile id, then job_profile_id is not there in json
                job_map = redisKeyMap[account_name]
                
                
                for key in job_map:
                    if "job_" in key:
                        if isinstance(job_map[key], dict):
                            if row["_id"] in job_map[key]:
                                job_profile_data = job_map[key]
                                del job_profile_data[row["_id"]]
                                redisKeyMap[account_name][key] = job_profile_data
                                local_dirtyMap[account_name][key] = {
                                    "redis_dirty" : True,
                                    "filter_dirty" : True
                                }
                                logger.critical("candidate removed from job deleted %s", row["_id"])
                                break

                
            
            
            if "ex_job_profile" in row:
                candidate_label = "Ex-" + row["ex_job_profile"]["name"]
                mapKey = "classify_" + candidate_label
                if mapKey not in redisKeyMap[account_name]:
                    candidate_data = r.get(mapKey)
                    if candidate_data:
                        candidate_data = json.loads(candidate_data)
                    else:
                        candidate_data = {}
                else:
                    candidate_data = redisKeyMap[account_name][mapKey]


                candidate_data[row["_id"]] = row
                redisKeyMap[account_name][mapKey] = candidate_data
                local_dirtyMap[account_name][mapKey] = {
                    "filter_dirty" : True,
                    "redis_dirty" : True
                }

            if candidate_label is not None:
                logger.critical("candidate labels %s", candidate_label)
                mapKey = "classify_" + candidate_label
                if mapKey not in redisKeyMap[account_name]:
                    candidate_data = r.get(mapKey)
                    if candidate_data:
                        candidate_data = json.loads(candidate_data)
                    else:
                        candidate_data = {}
                else:
                    candidate_data = redisKeyMap[account_name][mapKey]

                # if row["_id"] in candidate_data:
                candidate_data[row["_id"]] = row

                redisKeyMap[account_name][mapKey] = candidate_data

                if isFilterUpdateNeeded: 
                    local_dirtyMap[account_name][mapKey] = {
                        "filter_dirty" : True,
                        "redis_dirty" : True
                    }
                else:
                    local_dirtyMap[account_name][mapKey] = {
                        "filter_dirty" : True,
                        "redis_dirty" : True
                    }


    

    if findtype == "full":
        logger.critical("starting full sync")

        # r.set("full_data" , json.dumps(full_map , default=json_util.default))
        
        for job_profile_id in job_profile_map:
            logger.critical("filter sync job %s ", job_profile_id)
            r.set("job_" + job_profile_id  , json.dumps(job_profile_map[job_profile_id] , default=json_util.default))
            # ret = updateFilter({
            #     "id" : job_profile_id,
            #     "fetch" : "job_profile",
            #     "action" : "index",
            #     "account_name" : account_name,
            #     "account_config": account_config
            # })
            mapKey = "job_" + job_profile_id
            local_dirtyMap[account_name][mapKey] = {
                "filter_dirty" : True,
                "redis_dirty" : True
            }
            redisKeyMap[account_name][mapKey] = job_profile_map[job_profile_id]
            logger.critical("updating filter %s" , mapKey)

        for candidate_label in candidate_map:
            logger.critical("filter sync candidate_label %s ", candidate_label)
            r.set("classify_" + candidate_label  , json.dumps(candidate_map[candidate_label] , default=json_util.default))
            # ret = updateFilter({
            #     "id" : candidate_label,
            #     "fetch" : "candidate",
            #     "action" : "index",
            #     "account_name" : account_name,
            #     "account_config": account_config
            # })
            mapKey = "classify_" + candidate_label
            redisKeyMap[account_name][mapKey] = candidate_map[candidate_label] 
            local_dirtyMap[account_name][mapKey] = {
                "filter_dirty" : True,
                "redis_dirty" : True
            }
            logger.critical("updating filter %s" , mapKey)

        # logger.critical("full data filter")
        # addFilter({
        #     "id" : 0,
        #     "fetch" : "full_data",
        #     "action" : "index"
        # })
        logger.critical("full data completed %s", local_dirtyMap)

    # for t in threads:
    #     t.join()

    for account_name in local_dirtyMap:
        if account_name not in dirtyMap:
            dirtyMap[account_name] = {}
            
        for key in local_dirtyMap[account_name]:
            dirtyMap[account_name][key] = local_dirtyMap[account_name][key]

    logger.critical("######### process completed")
    is_queue_process_running =  False
    queue_process(True)


time_map = {}

def sendToSearchIndex(row, r, from_type, account_name, account_config):
    # if from_type == "full":
    # this gets slow with full when data is large
    #     return

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
        # logger.critical("add to search")
        if not r.exists(row['_id']):
            # if key exists in redis, this means before search was already indexed. the content doesn't change at all much
            t = Thread(target=addToSearch, args=(row["_id"],finalLines,{}, account_name, account_config))
            t.start()
            # this is getting slow...

def addFilter(obj, key, account_name, account_config, is_direct):
    global dirtyMap
    global time_map
    ignore = False

    if obj["action"] == "index":
        if obj["fetch"] not in time_map:
            time_map[obj["fetch"]] = {}

        id = obj["id"]
        if id not in time_map[obj["fetch"]]:
            time_map[obj["fetch"]][id] = time.time()
            logger.critical("added new fetch %s", id)
            ignore = True
            dirtyMap[account_name][key] = {
                "filter_dirty" : True,
                "redis_dirty" : False # True it was true before
            }
        else:
            ctime = time_map[obj["fetch"]][id]
            logger.critical("time for add Filter %s",  time.time() - ctime )
            if (time.time() - ctime) < 1 * 60 or is_direct:
                ignore = True
                dirtyMap[account_name][key] = {
                    "filter_dirty" : True,
                    "redis_dirty" : False # True it was true before
                }
                # see we are setting directy map. this means it will again trigger for sure
                logger.critical("ignoreed %s" , obj)
            else:
                time_map[obj["fetch"]][id] = time.time()
    else:
        logger.critical("different action found %s", obj)


    if not ignore:
        # try:
        # Thread(target=updateFilter, args=( obj , )).start() giving errors. 
        logger.critical("sending to filter mq")
        ret = updateFilter(obj)
        logger.critical("receieved from filter %s" , ret)
        # except Exception as e:
        #     logger.critical(str(e))
        #     traceback.print_exc(e)
    else:
        logger.critical("addfilter skipped")

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
