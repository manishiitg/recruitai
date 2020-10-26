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
import math 

def time_analysis(db, no_of_days_to_analyse, ids = None):
    if ids:
        ret = db.ai_stats.find({
            "queue_time" : {
                "$gt" : datetime.datetime.now() - datetime.timedelta(days=no_of_days_to_analyse)
            },
            "mongoid" : {
                "$in" : ids
            }
        })
    else:    
        ret = db.ai_stats.find({
            "queue_time" : {
                "$gt" : datetime.datetime.now() - datetime.timedelta(days=no_of_days_to_analyse)
            }
        })

    avg_speed_per_page = {}
    for row in ret:
        if "current_stage" not in row:
            row["current_stage"] = "summary" #temp code for old data

        if row["current_stage"] == "summary":
            if "image" in row["stage"]:
                if "meta" in row['stage']["image"]:
                    if "images" in row['stage']["image"]["meta"]:
                        no_of_images = row['stage']['image']['meta']['images']
                        
                        resume_processing_time = 0
                        for stage in row["stage"]:
                            if "time_spent" in row["stage"][stage]:
                                resume_processing_time += row["stage"][stage]["time_spent"]
                        
                        if no_of_images not in avg_speed_per_page:
                            avg_speed_per_page[no_of_images] = {
                                "time" : 0,
                                "count" : 0
                            }

                        avg_speed_per_page[no_of_images]["time"] += resume_processing_time
                        avg_speed_per_page[no_of_images]["count"] += 1
    
    for no_of_images in avg_speed_per_page:
        if avg_speed_per_page[no_of_images]["count"] != 0:
            avg_speed_per_page[no_of_images]["avg"] = avg_speed_per_page[no_of_images]["time"] / avg_speed_per_page[no_of_images]["count"]
        else:
            avg_speed_per_page[no_of_images]["avg"] = -1

    return avg_speed_per_page


def resume_analytics_single_candidate(id, account_name, account_config):
    db = initDB(account_name, account_config)
    # ret = db.emailStored.find_one({"_id" : ObjectId(id)})

    logger.critical("resume_analytics_single_candidate %s", id)
    
    ret = db.ai_stats_resume_time_analysis.find({
        "mongoid" : id
    })

    detail = {
        "resume_parsing_analysis" : [],
        "ai_stats" : []
    }
    for row in ret:
        time_analysis = row["time_analysis"]

        obj = {
            "total_page" : row["total_page"],
            "total_time" : row["total_time"],
            "insert_time": row["insert_time"],
            "parsing_type" : row["parsing_type"],
            "time_analysis" : {}
        }
        for key in time_analysis:
            obj["time_analysis"][key] = {
                "key" : key,
                "time_taken" : time_analysis[key]["time_taken"],
                "breakdown" : []
            }
            if "time" in time_analysis[key]:
                for idx in time_analysis[key]["time"]:
                    for key2 in time_analysis[key]["time"][idx].keys():
                        obj["time_analysis"][key]["breakdown"].append({      
                            "key" : key2 + "-" + str(idx),
                            "time" : time_analysis[key]["time"]
                        })
        
        detail['resume_parsing_analysis'].append(obj)

    ret = db.ai_stats.find({
        "mongoid" : id
    })
    for row in ret:
        
        obj = {
            "queue_time" : row["queue_time"].timestamp(),
            "queue_waiting" : row["queue_waiting"],
            "resume_processing_time": row["resume_processing_time"],
            "total_stages" : row["total_stages"],
            "time_analysis" : []
        }

        for key in row["stage"].keys():

            time = row["stage"][key]["time"]
            time_spent = -1
            if "time_spent" in row["stage"][key]:
                time_spent = row["stage"][key]["time_spent"]

            obj["time_analysis"].append({
                "stage": key,
                "time" : time,
                "time_spent" : time_spent
            })

        detail['ai_stats'].append(obj)

    return detail


def resume_only_parsing_speed(account_name, account_config):
    no_of_days_to_analyse = 30
    db = initDB(account_name, account_config)
    # add code for single resume based on id as well

    ret = db.ai_stats_resume_time_analysis.find({
        "parsing_type" : "full",
        "insert_time" : {
            "$gt" : datetime.datetime.now() - datetime.timedelta(days=no_of_days_to_analyse)
        }
    })

    resume_full_analysis = {}

    for row in ret:
        time_analysis = row["time_analysis"]
        for key in time_analysis:
            if key not in resume_full_analysis:
                resume_full_analysis[key] = {
                    "time_taken" : 0,
                    "count" : 0
                }

            resume_full_analysis[key]["time_taken"] += time_analysis[key]["time_taken"]
            resume_full_analysis[key]["count"] += 1
            if "time" in time_analysis[key]:
                time = time_analysis[key]["time"]
                for page in time:                    
                    for sub_key in time[page]:
                        key2 = key + "_" + sub_key
                        if key2 not in resume_full_analysis:
                            resume_full_analysis[key2] = {
                                "time_taken" : 0,
                                "count" : 0
                            }

                        resume_full_analysis[key2]["time_taken"] += time[page][sub_key]
                        resume_full_analysis[key2]["count"] += 1 


    for key in resume_full_analysis:
        if resume_full_analysis[key]["count"] > 0:
            resume_full_analysis[key]["avg"] = resume_full_analysis[key]["time_taken"] / resume_full_analysis[key]["count"]
        else:
            resume_full_analysis[key]["avg"] = -1
    

    ret = db.ai_stats_resume_time_analysis.find({
        "parsing_type" : "fast",
        "insert_time" : {
            "$gt" : datetime.datetime.now() - datetime.timedelta(days=no_of_days_to_analyse)
        }
    })

    resume_fast_analysis = {}

    for row in ret:
        time_analysis = row["time_analysis"]
        for key in time_analysis:
            if key not in resume_fast_analysis:
                resume_fast_analysis[key] = {
                    "time_taken" : 0,
                    "count" : 0
                }

            resume_fast_analysis[key]["time_taken"] += time_analysis[key]["time_taken"]
            resume_fast_analysis[key]["count"] += 1
            if "time" in time_analysis[key]:
                time = time_analysis[key]["time"]
                for page in time:
                    for sub_key in time[page]:
                        key2 = key + "_" + sub_key
                        if key2 not in resume_full_analysis:
                            resume_full_analysis[key2] = {
                                "time_taken" : 0,
                                "count" : 0
                            }

                        resume_full_analysis[key2]["time_taken"] += time[page][sub_key]
                        resume_full_analysis[key2]["count"] += 1 

    for key in resume_fast_analysis:
        if resume_fast_analysis[key]["count"] > 0:
            resume_fast_analysis[key]["avg"] = resume_fast_analysis[key]["time_taken"] / resume_fast_analysis[key]["count"]
        else:
            resume_fast_analysis[key]["avg"] = -1

    return {
        "resume_full_analysis" : resume_full_analysis,
        "resume_fast_analysis" : resume_fast_analysis
    }

def resume_parsing_speed_analysis(account_name, account_config):
    
    no_of_days_to_analyse = 30

    db = initDB(account_name, account_config)
    
    avg_speed_per_page = time_analysis(db , no_of_days_to_analyse)

    ret = db.emailStored.find({
        "cvParsedInfo.parsing_type" : "full",
        "date" : {
            "$gt" : datetime.datetime.now() - datetime.timedelta(days=no_of_days_to_analyse)
        }
    })
    mongoids = []
    for row in ret:
        mongoids.append(str(row["_id"]))
    
    full_speed_per_page = time_analysis(db , no_of_days_to_analyse, mongoids)


    ret = db.emailStored.find({
        "cvParsedInfo.parsing_type" : "fast",
        "date" : {
            "$gt" : datetime.datetime.now() - datetime.timedelta(days=no_of_days_to_analyse)
        }
    })
    mongoids = []
    for row in ret:
        mongoids.append(str(row["_id"]))
    
    fast_speed_per_page = time_analysis(db , no_of_days_to_analyse, mongoids)


    return {
        "avg_speed_per_page" : avg_speed_per_page,
        "fast_speed_per_page" : fast_speed_per_page,
        "full_speed_per_page" : full_speed_per_page
    }

def get_resume_parsed_per_month(account_name, account_config):

    
    db = initDB(account_name, account_config)
    

    ret = db.ai_stats.find({
        "queue_time" : {
            "$gt" : datetime.datetime.now() - datetime.timedelta(days=365)
        }
    })

    day_wise = {}
    for row in ret:
        
        queue_time = row["queue_time"]
        # days = (datetime.datetime.now() - queue_time).days
        # day = queue_time.strftime('%a')
        # week = math.ceil(days/7)
        month = queue_time.strftime('%b')
        year = queue_time.strftime('%Y')
        key = month + "-" + year
        if key not in day_wise:
            day_wise[key] = {
                "count" : 0,
                "month" : queue_time.strftime('%b'),
                "week" : queue_time.strftime('%Y')
            }
        
        day_wise[key]["count"] += 1

    return day_wise

def get_resume_parsed_per_week(account_name, account_config):

    
    db = initDB(account_name, account_config)
    resp = db.ai_stats.create_index([ ("queue_time", -1) ])

    ret = db.ai_stats.find({
        "queue_time" : {
            "$gt" : datetime.datetime.now() - datetime.timedelta(days=8*7)
        }
    })

    day_wise = {}
    for row in ret:
        
        queue_time = row["queue_time"]
        days = (datetime.datetime.now() - queue_time).days
        day = queue_time.strftime('%a')
        week = math.ceil(days/7)
        month = queue_time.strftime('%b')
        key = str(week) + "-" + month
        if key not in day_wise:
            day_wise[key] = {
                "count" : 0,
                "month" : queue_time.strftime('%b'),
                "week" : week
            }
        
        day_wise[key]["count"] += 1

    return day_wise

def get_resume_parsed_per_day(account_name, account_config):
    
    db = initDB(account_name, account_config)
    resp = db.ai_stats.create_index([ ("queue_time", -1) ])
    ret = db.ai_stats.find({
        "queue_time" : {
            "$gt" : datetime.datetime.now() - datetime.timedelta(days=8)
        }
    })

    day_wise = {}
    for row in ret:
        queue_time = row["queue_time"]
        day = queue_time.strftime('%a')
        if day not in day_wise:
            day_wise[day] = {
                "count" : 0,
                "date" : queue_time.strftime('%d'),
                "month" : queue_time.strftime('%b')
            }
        
        day_wise[day]["count"] += 1

    return day_wise

def current_candidate_status(mongoid, account_name, account_config):
    db = initDB(account_name, account_config)
    row = db.ai_stats.find_one({"mongoid" : mongoid})
    if not row:
        return {
            "error" : f"{mongoid} not found "
        }
    old_resumes = db.ai_stats.find({"current_stage" : "summary"}).sort("queue_time", -1).limit(1)
    for old_resume in old_resumes:
        break 

    no_total_stages = old_resume["total_stages"]
    total_stags_steps = list(old_resume['stage'].keys())
    if "current_stage" not in row:
        current_stage = "summary" # old data
    else: 
        current_stage = row["current_stage"]
    queue_time = row['queue_time']
    priority = row["priority"]

    days = (datetime.datetime.now() - queue_time).days

    in_progress, in_error, progress_status = get_progress_stats(db)

    in_process = False
    is_waiting = False
    is_stuck = False
    in_completed = False
    if current_stage == "queue":
        is_waiting = True
    else:
        if days > 2 and current_stage != "summary":
            is_stuck = True
        elif current_stage == "summary":
            in_completed = True
        else:
            in_process = True

    return {
        "in_process" : in_process,
        "is_waiting" : is_waiting,
        'is_stuck' : is_stuck,
        "in_completed" : in_completed,
        "priority" : priority,
        "queue_time": queue_time.timestamp(),
        "queue_time_friendly" : datetime.datetime.utcfromtimestamp(queue_time.timestamp()).strftime("%Y-%m-%d %H:%M:%S") ,
        "current_stage" : current_stage,
        "total_stags_steps" : total_stags_steps,
        "no_total_stages" : no_total_stages,
        "resumes_in_process" : len(in_progress)
    }

def ai_queue_count(account_name, account_config):
    db = initDB(account_name, account_config)
    total = db.ai_stats.count({})
    total_queue = queued = db.ai_stats.count({"current_stage": "queue"})
    total_finished = queued = db.ai_stats.count(
        {"$or" : [
            {"current_stage": "summary"},
            {"current_stage": { "$exists" : False }}  # this condition is mainly for old data
        ]}
    )
    
    in_progress, in_error, progress_status = get_progress_stats(db)

    full_parsing_count = db.emailStored.count({"cvParsedInfo.parsing_type" : "full"})
    fast_parsing_count = db.emailStored.count({"cvParsedInfo.parsing_type" : "fast"})
        
        # print(row)
        # break
    
    
    return {
        "total" : total,
        "total_queue" : total_queue,
        "total_finished" : total_finished,
        "total_in_process": len(in_progress),
        "total_in_error": len(in_error),
        "in_progress" : in_progress,
        "in_error": in_error,
        "progress_status" : progress_status,
        "full_parsing_count" : full_parsing_count,
        "fast_parsing_count" : fast_parsing_count
    }


def get_progress_stats(db):
    ret = db.ai_stats.find({
        "current_stage" : {
            "$exists" : True,
            "$nin" : ["summary",'queue']
        }
    })
    in_progress = []
    in_error = []
    progress_status = {}
    for row in ret:
        row["_id"] = str(row["_id"])
        del row["stage"]
        queue_time = row["queue_time"]
        row["days"] = (datetime.datetime.now() - queue_time).days
        if row["days"] >= 1:
            in_error.append(json.loads(json.dumps(row, default=str)))
        else:
            in_progress.append(json.loads(json.dumps(row, default=str)))
            current_stage = row["current_stage"]
            if current_stage not in progress_status:
                progress_status[current_stage] = 0
            
            progress_status[current_stage] += 1

    return in_progress, in_error, progress_status