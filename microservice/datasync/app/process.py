import os
from threading import Thread

from app.publishsearch import sendBlockingMessage

from bson import json_util

from pymongo import MongoClient
from bson.objectid import ObjectId

from app.logging import logger
import json

from bson import json_util


client = MongoClient(os.environ.get("RECRUIT_BACKEND_DB" , "mongodb://176.9.137.77:27017/hr_recruit_dev"))
db = client[os.environ.get("RECRUIT_BACKEND_DATABASE" , "hr_recruit_dev")]

import redis
r = redis.Redis(host=os.environ.get("REDIS_HOST","redis"), port=os.environ.get("REDIS_PORT",6379), db=0)



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



        r.set(row["_id"]  , json.dumps(row,default=json_util.default))

        if job_profile_id is not None:
            if job_profile_id not in job_profile_map:
                job_profile_map[job_profile_id] = []

            job_profile_map[job_profile_id].append(row)

        if len(finalLines) == 0:
            finalLines = [
                row["subject"],
                row["from"],
                row["sender_mail"]
            ]    
        
        
        if findtype == "syncCandidate":
            t = Thread(target=addToSearch, args=(row["_id"],finalLines,{}))
            t.start()
            t.join() 

            # this is very very slow for full job profile 
            # need to add bulk to search or something

            # no need of tread or async way so that we can reuse connection for pika
            # if we use threads then many threads start even before connection is created 
            # so they create multiple connections
            threads.append(t)
        
    if findtype != "syncCandidate":
        if job_profile_id is not None:
            for job_profile_id in job_profile_map:
                ret = r.set("job_" + job_profile_id  , json.dumps(job_profile_map[job_profile_id] , default=json_util.default))
                logger.info(ret)


    for t in threads:
        t.join()

        

def addToSearch(mongoid, finalLines, ret):
    sendBlockingMessage({
        "id": mongoid,
        "lines" : finalLines,
        "extra_data" : ret,
        "action" : "addDoc"
    })