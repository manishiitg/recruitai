from app.logging import logger
import redis

import os
import json

from bson.objectid import ObjectId
from pymongo import MongoClient

import datetime

from app.account import initDB

import time
import requests
import datetime
from requests.auth import HTTPBasicAuth
RabbitMQLOGIN = os.getenv("RABBIT_LOGIN")
amqp_url_base = os.getenv('RABBIT_API_URL')


def ai_queue_count():
    db = initDB(account_name, account_config)
    total = db.ai_stats.count({})
    total_queue = queued = db.ai_stats.count({"current_stage": "queue"})
    return {
        "total" : total,
        "total_queue" : total_queue
    }

def update_resume_time_analysis(resume_unique_key, time_analysis, mongoid, parsing_type, account_name, account_config):
    
    res = requests.get(amqp_url_base + "/api/queues", verify=False, auth=HTTPBasicAuth(RabbitMQLOGIN.split(":")[0], RabbitMQLOGIN.split(":")[1]))
    queues = res.json()

    running_process = 0
    mq_status = {}
    for queue in queues:
        if queue["name"] == "resume" or queue["name"] == "image" or queue["name"] == "picture" or queue["name"] == "summary":
            
            print(queue)
            if "consumers" in queue.keys():
                mq_status[queue["name"]] = {
                    "consumers" : queue["consumers"],
                    "in_process" : queue["messages_unacknowledged_ram"]
                }
                running_process += int(queue["messages_unacknowledged_ram"])

    db = initDB(account_name, account_config)

    resume_unique_key = resume_unique_key.split(".")[0]
    # incase of file .docx gets converted .pdf which causes issues

    total_time = 0
    total_page =  0

    if "time" in time_analysis["resume_construction"]:
        total_page = len(time_analysis["resume_construction"]["time"])

    
    for key in time_analysis:
        total_time += float(time_analysis[key]["time_taken"])

    db.ai_stats_resume_time_analysis.insert_one({
        "resume_unique_key" : resume_unique_key,
        "time_analysis" : time_analysis,
        "mongoid" : mongoid,
        "insert_time" : datetime.datetime.now(),
        "mq_status" : mq_status,
        "running_process": running_process,
        "total_time" : total_time,
        "total_page" : total_page,
        "parsing_type" : parsing_type
    })





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
        is_training = False
        if "training" in stage["meta"]:
            is_training = True

        priority = -1

        mongoid = ""
        if "mongoid" in meta:
            mongoid = meta["mongoid"]

        if "priority" in stage.keys():
            priority = stage["priority"]

        db.ai_stats.insert_one({
            "resume_unique_key" : resume_unique_key,
            "stage" : {
                stage["pipeline"] : stage
            },
            "is_training" : is_training,
            "priority" : priority,
            "mongoid" : mongoid,
            "queue_time" : datetime.datetime.now(),
            "current_stage" : stage["pipeline"]
        })
    else:
        oldstage = row["stage"]
        
        name = stage["pipeline"]
            
        

        if "_start" not in name:
            stage["time_spent"] = -1
            for key in list(oldstage.keys()):
                if key == name + "_start":
                    if "time" not in oldstage[key]:
                        oldstage[key]["time"] = 0  # this should not happen at all. dont why its happening

                    stage["time_spent"] = stage["time"] - oldstage[key]["time"]
                    break
        else:
            stage["time_spent"] = 0
            
        oldstage[stage["pipeline"]] = stage

        resume_processing_time = 0
        queue_waiting = 0
        if len(oldstage) > 1 and "queue" in oldstage:
            if "image_start" in oldstage:
                queue_waiting = oldstage["image_start"]["time"] - oldstage["queue"]["time"]
                resume_processing_time = stage["time"] - oldstage["image_start"]["time"]

        db.ai_stats.update_one({
            "resume_unique_key" : resume_unique_key
        }, {
            "$set" : {
                "stage" : oldstage,
                "queue_waiting" : queue_waiting,
                "resume_processing_time" : resume_processing_time,
                "total_stages" : len(oldstage),
                "current_stage" : stage["pipeline"]
            }
        })