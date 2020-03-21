import os
from threading import Thread

from app.publishsearch import sendBlockingMessage

from pymongo import MongoClient
from bson.objectid import ObjectId

from app.logging import logger
import json

from bson import json_util


client = MongoClient(os.environ.get("RECRUIT_BACKEND_DB" , "mongodb://176.9.137.77:27017/hr_recruit_dev"))
db = client[os.environ.get("RECRUIT_BACKEND_DATABASE" , "hr_recruit_dev")]

import redis
r = redis.Redis(host=os.environ.get("REDIS_HOST","redis"), port=os.environ.get("REDIS_PORT",6379), db=0)

def moveKey(candidate_id, from_key, to_key):
    from_job_profile_data = r.get(from_key)
    from_job_profile_data = json.loads(from_job_profile_data)

    to_job_profile_data = r.get(to_key)
    to_job_profile_data = json.loads(to_job_profile_data)

    del from_job_profile_data[candidate_id]

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
    
def process(findtype = "", mongoid = None):
    threads = []
    # "job_profile_id": mongoid
    if findtype == "syncCandidate":
        logger.info("syncCandidate")
        ret = db.emailStored.find({ 
            "_id" : ObjectId(mongoid),
            "cvParsedInfo.debug" : {"$exists" : True} } , 
            {"body": 0}
        )
    elif findtype == "syncJobProfile":
        logger.info("syncJobProfile")
        job_profile_id = mongoid
        
        ret = db.emailStored.find({ 
            "job_profile_id" : mongoid,
            "cvParsedInfo.debug" : {"$exists" : True} } , 
           {"body": 0}
        )
    else:
        logger.info("full")
        ret = db.emailStored.find({ 
            "cvParsedInfo.debug" : {"$exists" : True} } , 
            {"body": 0}
        )


    job_profile_map = {}
    candidate_map = {}

    for row in ret:
        row["_id"] = str(row["_id"])
        logger.info(row["_id"])
        if "job_profile_id" in row:
            job_profile_id = row["job_profile_id"]
        else:
            job_profile_id = None

        cvParsedInfo = row["cvParsedInfo"]
        finalLines = []
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

        r.set(row["_id"]  , json.dumps(row,default=json_util.default))

        if job_profile_id is not None:
            if job_profile_id not in job_profile_map:
                job_profile_map[job_profile_id] = {}

            job_profile_map[job_profile_id][row["_id"]] = row

        if len(finalLines) == 0:
            finalLines = [
                row["subject"],
                row["from"],
                row["sender_mail"]
            ]    
        
        
        if findtype == "syncCandidate":
            job_profile_data_existing = r.get("job_" + job_profile_id)

            job_profile_data_now = json.dumps(row,default=json_util.default)

            if job_profile_data_existing != job_profile_data_now:
                logger.info("add to searhch")
                t = Thread(target=addToSearch, args=(row["_id"],finalLines,{}))
                t.start()
                t.join() 
            else:
                logger.info("skip add to searhch")

            # this is very very slow for full job profile 
            # need to add bulk to search or something

            # no need of tread or async way so that we can reuse connection for pika
            # if we use threads then many threads start even before connection is created 
            # so they create multiple connections
            # threads.append(t)

            if job_profile_id is not None:
                job_profile_data = r.get("job_" + job_profile_id)
                job_profile_data = json.loads(job_profile_data)

                if row["_id"] in job_profile_data:
                    job_profile_data[row["_id"]] = row
                
            if candidate_label is not None:
                logger.info(candidate_label)
                candidate_data = r.get("classify_" + candidate_label)
                candidate_data = json.loads(candidate_data)

                if row["_id"] in candidate_data:
                    candidate_data[row["_id"]] = row


                # there is one case here. if candidate changes job profile, we need to remove it from previous job as well
                # this will be handled via a seperate api

    
        

    if findtype == "syncJobProfile":
        if job_profile_id is not None:
            for job_profile_id in job_profile_map:
                ret = r.set("job_" + job_profile_id  , json.dumps(job_profile_map[job_profile_id] , default=json_util.default))
                logger.info(ret)
    
    if findtype == "full":
        for job_profile_id in job_profile_map:
            r.set("job_" + job_profile_id  , json.dumps(job_profile_map[job_profile_id] , default=json_util.default))

        for candidate_label in candidate_map:
            r.set("classify_" + candidate_label  , json.dumps(candidate_map[candidate_label] , default=json_util.default))


    # for t in threads:
    #     t.join()

        

def addToSearch(mongoid, finalLines, ret):
    sendBlockingMessage({
        "id": mongoid,
        "lines" : finalLines,
        "extra_data" : ret,
        "action" : "addDoc"
    })