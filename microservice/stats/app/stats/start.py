from app.logging import logger
import redis

import os
import json

from bson.objectid import ObjectId
from pymongo import MongoClient

import datetime

from app.account import initDB

import time



def resume_pipeline_update(resume_unique_key, stage, meta, account_name, account_config):
    db = initDB(account_name, account_config)


    resume_unique_key = resume_unique_key.split(".")[0]
    # incase of file .docx gets converted .pdf which causes issues

    stage["time"] = time.time()

    if "account_name" in meta:
        del meta["account_name"]

    if "account_config" in meta:
        del meta["account_config"]


    stage["meta"] = meta

    row = db.ai_stats.find_one({"resume_unique_key" : resume_unique_key})

    if not row:
        db.ai_stats.insert_one({
            "resume_unique_key" : resume_unique_key,
            "stage" : [stage],
        })
    else:
        oldstage = row["stage"]
        

        stage["time_spent"] = stage["time"] - oldstage[-1]["time"]
        oldstage.append(stage)

        resume_processing_time = -1
        queue_waiting = -1
        if len(oldstage) > 1:
            queue_waiting = oldstage[1]["time"] - oldstage[0]["time"]
            resume_processing_time = stage["time"] - oldstage[1]["time"]

        db.ai_stats.update_one({
            "resume_unique_key" : resume_unique_key
        }, {
            "$set" : {
                "stage" : oldstage,
                "queue_waiting" : queue_waiting,
                "resume_processing_time" : resume_processing_time,
                "total_stages" : len(oldstage)
            }
        })