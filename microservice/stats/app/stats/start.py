from app.logging import logger
import redis

import os
import json

from bson.objectid import ObjectId
from pymongo import MongoClient

db = None
def initDB():
    global db
    if db is None:
        client = MongoClient(os.getenv("RECRUIT_BACKEND_DB")) 
        db = client[os.getenv("RECRUIT_BACKEND_DATABASE")]

    return db



def start():

    db = initDB()


    candidates = db.emailStored.find({ "pipeline" : { "$exists" : True } } , { "body" : 0} )

    stagesTime = {}
    for cand in candidates:
        for pipe in cand["pipeline"]:
            # if pipe["stage"] == 0:
            #     start_time = pipe["start_time"]

            if "timeTaken" in pipe:
                if pipe["stage"] not in stagesTime:
                    stagesTime[pipe["stage"]] = []

                stagesTime[pipe["stage"]].append(pipe["timeTaken"])

    ret = {}
    for stage_no in stagesTime:
        total = 0
        for t in stagesTime[stage_no]:
            total += t

        ret[stage_no] = total/len(stagesTime[stage_no])

    print(ret)
    # no of pending cv's
    # no of cv's complete
    # ai version
    # pipeline analysis i.e avg time taken for each pipeline
    # search index stats
    # redis index stats
    pass
