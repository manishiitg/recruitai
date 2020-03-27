import os
from threading import Thread

from app.publishsearch import sendBlockingMessage
from app.publishfilter import sendBlockingMessage as updateFilter

from pymongo import MongoClient
from bson.objectid import ObjectId

from app.logging import logger
import json
import os
from bson import json_util

import traceback
import time

db = None
def initDB():
    global db
    if db is None:
        client = MongoClient(os.getenv("RECRUIT_BACKEND_DB")) 
        db = client[os.getenv("RECRUIT_BACKEND_DATABASE")]

    return db

import redis
r = redis.StrictRedis(host=os.environ.get("REDIS_HOST","redis"), port=os.environ.get("REDIS_PORT",6379), db=0, decode_responses=True)


def moveKey(candidate_id, from_key, to_key):
    from_job_profile_data = r.get(from_key)
    from_job_profile_data = json.loads(from_job_profile_data)

    to_job_profile_data = r.get(to_key)
    to_job_profile_data = json.loads(to_job_profile_data)

    del from_job_profile_data[candidate_id]
    db = initDB()
    row = db.emailStored.find_one({ 
            "_id" : ObjectId(candidate_id) } , 
            {"body": 0}
        )
    if row:
        to_job_profile_data[candidate_id] = row
        r.set(candidate_id  , json.dumps(row,default=json_util.default))
        to_job_profile_data[candidate_id] = row

    r.set(from_key  , json.dumps(from_job_profile_data , default=json_util.default))
    r.set(to_key  , json.dumps(to_job_profile_data , default=json_util.default))

def classifyMoved(candidate_id, from_id, to_id):
    moveKey(candidate_id, "classify_" + from_id, "classify_" + to_id)

def syncJobProfileChange(candidate_id, from_id, to_id):
    moveKey(candidate_id, "job_" + from_id, "job_" + to_id)
    

# recentProcessList = {}

def process(findtype = "full", mongoid = ""):
    threads = []
    # "job_profile_id": mongoid

    # global recentProcessList

    # if findtype != "full":
    #     recentProcessList[mongoid+"-"+findtype] = time.time()

    db = initDB()
    if findtype == "syncCandidate":
        logger.info("syncCandidate")
        ret = db.emailStored.find({ 
            "_id" : ObjectId(mongoid),
             } , 
            {"body": 0}
        )
    elif findtype == "syncJobProfile":
        logger.info("syncJobProfile")
        job_profile_id = mongoid
        
        ret = db.emailStored.find({ 
            "job_profile_id" : mongoid,
            # "cvParsedInfo.debug" : {"$exists" : True} 
            } , 
           {"body": 0}
        )
    else:
        logger.info("full")
        # r.flushdb()
        # this is wrong. this remove much more data like resume parsed information etc
        
        for key in r.scan_iter():
            if "candidate_" in key or "job_" in key:
                r.delete(key)
                
        ret = db.emailStored.find({ } , 
            {"body": 0}
        )


    job_profile_map = {}
    candidate_map = {}

    full_map = {}

    for row in ret:
        row["_id"] = str(row["_id"])
        # logger.info(row["_id"])
        if "job_profile_id" in row and len(row["job_profile_id"]) > 0:
            job_profile_id = row["job_profile_id"]
        else:
            job_profile_id = None
        

        r.set(row["_id"]  , json.dumps(row,default=json_util.default))

        finalLines = []
        if "cvParsedInfo" in row:
            cvParsedInfo = row["cvParsedInfo"]
            if "newCompressedStructuredContent" in cvParsedInfo:
                for page in cvParsedInfo["newCompressedStructuredContent"]:
                    for pagerow in cvParsedInfo["newCompressedStructuredContent"][page]:
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

        


        full_map[row["_id"]] = row
        if job_profile_id is not None:
            if job_profile_id not in job_profile_map:
                job_profile_map[job_profile_id] = {}

            job_profile_map[job_profile_id][row["_id"]] = row

        if len(finalLines) == 0:
            if "subject" not in row:
                row["subject"] = ""
            
            if "sender_mail" not in row:
                row["sender_mail"] = ""

            if "from" not in row:
                row["from"] = ""

            finalLines = [
                row["subject"],
                row["from"],
                row["sender_mail"]
            ]    
        
        
        if findtype == "syncCandidate":
            # if job_profile_id:
            #     job_profile_data_existing = r.get("job_" + job_profile_id)
            #     job_profile_data_now = json.dumps(row,default=json_util.default)

            if len(finalLines) > 0:
                logger.info("add to searhch")
                t = Thread(target=addToSearch, args=(row["_id"],finalLines,{}))
                t.start()
                # t.join() 
                # this is getting slow...

            # this is very very slow for full job profile 
            # need to add bulk to search or something

            # no need of tread or async way so that we can reuse connection for pika
            # if we use threads then many threads start even before connection is created 
            # so they create multiple connections
            # threads.append(t)

            if job_profile_id is not None:
                job_profile_data = r.get("job_" + job_profile_id)
                if job_profile_data:
                    job_profile_data = json.loads(job_profile_data)
                else:
                    job_profile_data = {}

                if row["_id"] in job_profile_data:
                    job_profile_data[row["_id"]] = row

                addFilter({
                    "id" : job_profile_id,
                    "fetch" : "job_profile",
                    "action" : "index"
                })
                
            if candidate_label is not None:
                logger.info(candidate_label)
                candidate_data = r.get("classify_" + candidate_label)
                if candidate_data:
                    candidate_data = json.loads(candidate_data)
                else:
                    candidate_data = {}

                if row["_id"] in candidate_data:
                    candidate_data[row["_id"]] = row

                addFilter({
                    "id" : candidate_label,
                    "fetch" : "candidate",
                    "action" : "index"
                })

                # there is one case here. if candidate changes job profile, we need to remove it from previous job as well
                # this will be handled via a seperate api

    
        

    if findtype == "syncJobProfile":
        if job_profile_id is not None:
            for job_profile_id in job_profile_map:
                logger.info("job profile key %s", "job_" + job_profile_id)

                ret = r.set("job_" + job_profile_id  , json.dumps(job_profile_map[job_profile_id] , default=json_util.default))
                logger.info(ret)

                logger.info("job profile filter")
                addFilter({
                    "id" : job_profile_id,
                    "fetch" : "job_profile",
                    "action" : "index"
                })
                logger.info("job profile filter completed")
    
    if findtype == "full":

        # r.set("full_data" , json.dumps(full_map , default=json_util.default))
        
        for job_profile_id in job_profile_map:
            logger.info("filter sync job %s ", job_profile_id)
            r.set("job_" + job_profile_id  , json.dumps(job_profile_map[job_profile_id] , default=json_util.default))
            ret = updateFilter({
                "id" : job_profile_id,
                "fetch" : "job_profile",
                "action" : "index"
            })
            logger.info("updating filter %s" , ret)

        for candidate_label in candidate_map:
            logger.info("filter sync candidate_label %s ", candidate_label)
            r.set("classify_" + candidate_label  , json.dumps(candidate_map[candidate_label] , default=json_util.default))
            ret = updateFilter({
                "id" : candidate_label,
                "fetch" : "candidate",
                "action" : "index"
            })
            logger.info("updating filter %s" , ret)

        # logger.info("full data filter")
        # addFilter({
        #     "id" : 0,
        #     "fetch" : "full_data",
        #     "action" : "index"
        # })
        logger.info("full data completed")

    # for t in threads:
    #     t.join()

time_map = {}

def addFilter(obj):
    ignore = False
    if obj["action"] == "index":
        if obj["fetch"] not in time_map:
            time_map[obj["fetch"]] = {}

        id = obj["id"]
        if id not in time_map[obj["fetch"]]:
            time_map[obj["fetch"]][id] = time.time()
        else:
            ctime = time_map[obj["fetch"]][id]
            logger.info("time for %s for obj %s",  time.time() - ctime , obj )
            if time.time() - ctime < 10 * 60:
                ignore = True
                logger.info("ignoreed %s" , obj)
            else:
                time_map[obj["fetch"]][id] = time.time()

    if not ignore:
        try:
            t = Thread(target=updateFilter, args=( obj , ))
            t.start()
            # updateFilter(obj)
        except Exception as e:
            logger.critical(str(e))
            traceback.print_exc(e)
    

def addToSearch(mongoid, finalLines, ret):
    try:
        sendBlockingMessage({
            "id": mongoid,
            "lines" : finalLines,
            "extra_data" : ret,
            "action" : "addDoc"
        })
    except Exception as e:
        logger.critical(str(e))
        traceback.print_exc(e)
