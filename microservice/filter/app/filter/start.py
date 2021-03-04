from app.logging import logger
from pymongo import MongoClient

from app.filter.util import parse_experiance_years, matchCourse, designation, location, getExperianceRange, getEducationFilters, getPassoutYearFilters, getGenderFilter, get_dob_filter

import os
import redis
import json
import time
from threading import Thread

from app.filter.util import getCourseDict
from datetime import datetime, timedelta
from calendar import monthrange

from app.account import connect_redis, initDB, r_set, r_get, r_exists, r_scan_iter

import requests
import hashlib   
from app.datasyncpublisher import sendMessage as datasync

from app.filter.email_name_phone import process_name, email_check_db, fix_phone
from bson.objectid import ObjectId

def fix_name_email_phone_all(account_name, account_config):
    db = initDB(account_name, account_config)
    
    rows = db.emailStored.find({"cvParsedInfo" : {"$exists": True}})
    for row in rows:
        # if str(row["_id"]) == "600d9e3126f614003baee93e":
        process_name(row, db, account_name, account_config)
        email_check_db(row, db)
        fix_phone(row, db)


def fix_name_email_phone(id, account_name, account_config):
    db = initDB(account_name, account_config)
    if not ObjectId.is_valid(id):
        return None

    row = db.emailStored.find_one(
        {"_id": ObjectId(id)}
    )
    if row:
        process_name(row, db, account_name, account_config)
        email_check_db(row, db)
        fix_phone(row, db)

def get_speedup_api(redisKey, url, payload, access_token, account_name, account_config):

    
    r = connect_redis(account_name, account_config)
    try:
        if len(payload) == 0:
            logger.critical("get request to %s", url)
            data = requests.get(url + "?accessToken=" + access_token, timeout=10)
            data = data.json()
            logger.critical("data %s", data)
            data = json.dumps(data)
        else:
            logger.critical("post request to %s with payload %s", url, payload)
            data = requests.post(url + "?accessToken=" + access_token , data = payload, timeout=10)
            data = data.json()
            logger.critical("data %s", data)
            data = json.dumps(data)
        
        logger.critical("updating redis data for get speed up api")
        r_set(redisKey, data, account_name, account_config) #  , ex=1 * 60 * 60expire in 1hr automatic
        return data
    except Exception as e:
        logger.critical("error in api %s %s", url, str(e))
        return json.dumps("error" + str(e))
    

    

def general_api_speed_up(url, payload, access_token, account_name, account_config):

    # + access_token.encode('utf-8')
    redisKey = "jb_" + hashlib.md5(  (url + json.dumps(payload)).encode('utf-8') ).hexdigest()
    r = connect_redis(account_name, account_config)
    print("checking for redis key")
    try:
        
        if r_exists(redisKey, account_name, account_config):
            logger.critical("speed up data returned from redis %s", redisKey)
            t = Thread(target = get_speedup_api, args=(redisKey, url, payload, access_token, account_name, account_config))
            t.start()
            data = r_get(redisKey, account_name, account_config)
            if data:
                print("not returning data from cache")
                return data

    except Exception as e:
        logger.critical("critical error %s", e)
        pass
    
    logger.critical("no redis data calling api directly")
    data = get_speedup_api(redisKey, url, payload, access_token, account_name, account_config)
    return data


# def get_job_overview(url, tag_id, access_token, redisKey , r):
#     url = url + "tag/" + tag_id + "?accessToken=" + access_token
#     data = requests.get(url)
#     data = data.json()
#     data = json.dumps(data)
#     r_set(redisKey, data , account_name, account_config, ex=1 * 60 * 60) #expire in 1hr automatic
#     logger.critical("updated job overview redis key %s", redisKey)

#     return data

# def syncTagData(tag_id, url, access_token, account_name, account_config):
#     r = connect_redis(account_name, account_config)

#     if url[-1] != "/":
#         url = url + "/"

#     redisKey = "jb_" + tag_id + ''.join(e for e in url if e.isalnum())

#     if r_exists(redisKey, account_name, account_config):
#         logger.critical("job overview data returned from redis %s", redisKey)
#         t = Thread(target = get_job_overview, args=(url, tag_id, access_token, redisKey , r))
#         t.start()
#         return r_get(redisKey, account_name, account_config)
    
#     data = get_job_overview(url, tag_id, access_token, redisKey , r)
#     return data


    



use_unique_cache_feature = True
use_unique_cache_only_for_classify_data = True
use_unique_cache_only_for_ai_data = True


def generateClassifyList(account_name, account_config):
    db = initDB(account_name, account_config)

    ret = db.emailStored.find({ } , {"body": 0, "cvParsedInfo.debug": 0})
    # if 'job_profile_id' in row:
    # this is because all logic below assumes job_profile_id is not there if no job

    candidate_map = {}
    candidate_len_map = {}
    for row in ret:
        if 'job_profile_id' in row:
            if len(row['job_profile_id'].strip()) == 0:
                del row['job_profile_id']

        if "cvParsedInfo" in row:
            cvParsedInfo = row["cvParsedInfo"]
            if "debug" in cvParsedInfo:
                del row["cvParsedInfo"]["debug"]

        if "job_profile_id" in row and len(row["job_profile_id"]) > 0:
            job_profile_id = row["job_profile_id"]
        else:
            if "ex_job_profile" not in row:
                # logger.critical("job profile not found!!!")
                job_profile_id = None

                mapKey = "NOT_ASSIGNED"
                if mapKey not in candidate_len_map:
                    candidate_len_map[mapKey] = 0
                    
                is_old = False
                month_year = ""
                is_year_old = False
                days = 0

                if "email_timestamp" in row:
                    timestamp_seconds = int(row["email_timestamp"])/1000
                    month_year = "-" +  datetime.fromtimestamp(timestamp_seconds).strftime('%Y-%b')
                    days =  abs(time.time() - timestamp_seconds)  / (60 * 60 * 24 )

                    if days < 30:
                        is_old = False
                    else:
                        is_old = True
                        # if days > 365:
                            # is_year_old = True
                        month_year = "-" +  datetime.fromtimestamp(timestamp_seconds).strftime('%Y')
                            # month_year = ":OLD"

                    

                else:
                    is_old = False
                
                if is_old:
                    mapKey = "NOT_ASSIGNED" + month_year
                
                if not is_old:
                    # skipping old candidates for now 
                    candidate_label = mapKey
                    
                    if candidate_label not in candidate_len_map:
                        candidate_len_map[candidate_label] = 0
                    
                    candidate_len_map[candidate_label] += 1
            
            
        is_year_old = False
        if "ex_job_profile" in row:
            continue # skipping ex job profile for now 
            if row["ex_job_profile"] and "name" in row["ex_job_profile"]:
                candidate_label = "Ex:" + row["ex_job_profile"]["name"]
                mapKey = candidate_label
                days = 0
                
                if candidate_label not in candidate_len_map:
                    candidate_len_map[candidate_label] = 0
                    
                    

                if "email_timestamp" in row:
                    timestamp_seconds = int(row["email_timestamp"])/1000
                    month_year = "-" +  datetime.fromtimestamp(timestamp_seconds).strftime('%Y') # remove moth for ex. only year based

                    cur_time = time.time()
                    days =  abs(cur_time - timestamp_seconds)  / (60 * 60 * 24 )

                    
                    if days > 365:
                        is_year_old = True
                        month_year = "-" +  datetime.fromtimestamp(timestamp_seconds).strftime('%Y')
                    
                    mapKey = mapKey + month_year
                
                

                candidate_label = mapKey

                if candidate_label not in candidate_len_map:
                    candidate_len_map[candidate_label] = 0
                    
                candidate_len_map[candidate_label] += 1

        candidate_label = None
        if "candidateClassify" in row:
            if "label" in row["candidateClassify"]:
                candidate_label = row["candidateClassify"]["label"]
                

                if str(candidate_label) == "False":
                    candidate_label = None
                else:
                    if candidate_label not in candidate_len_map:
                        candidate_len_map[candidate_label] = 0

                if candidate_label:
                    # month_year = ""
                    # is_year_old = False
                    # days = 0
                    # if "email_timestamp" in row:
                    #     timestamp_seconds = int(row["email_timestamp"])/1000
                    #     month_year = "-" +  datetime.fromtimestamp(timestamp_seconds).strftime('%Y-%b')

                    #     cur_time = time.time()
                    #     days =  abs(cur_time - timestamp_seconds)  / (60 * 60 * 24 )

                    #     if days > 15:
                    #         if days > 365:
                    #             is_year_old = True
                    #             month_year = "-" +  datetime.fromtimestamp(timestamp_seconds).strftime('%Y')
                    
                    # candidate_label = candidate_label + month_year

                    
                    if candidate_label not in candidate_len_map:
                        candidate_len_map[candidate_label] = 0
                    
                    candidate_len_map[candidate_label] += 1
                    
    return candidate_len_map
            
def get_candidate_tags_v2(account_name, account_config):
    r = connect_redis(account_name, account_config)

    tag_map = {
        "NOT_ASSIGNED" : "No Job Assigned",
        "softwaredevelopment" : "Software Development",
        "HRRecruitment" : "HR",
        "accounts" : "Accounts",
        "Sales" : "Sales",
        "legal" : "Legal",
        "marketing" : "Marketing",
        "customerservice" : "Customer Service",
        "TeachingEducation" : "Education",
    }

    response = []

    classify_tags = []

    classify_list = []
    if r_exists("classify_list", account_name, account_config): 
        classify_list = r_get("classify_list", account_name, account_config)
        classify_list = json.loads(classify_list)
    else:
        candidate_len_map = generateClassifyList(account_name, account_config)
        classify_list = list(set(list(candidate_len_map.keys())))
        r_set('classify_list', json.dumps(classify_list), account_name, account_config)

        for tag in candidate_len_map:
            r_set("classify_" + tag + "_len" , candidate_len_map[tag], account_name, account_config)



    def score_tag_idx(x):
        x = x.replace("classify_","")
        if "-" in x:
            actual_tag = x.split("-")[0]
            tag_idx = 1
            for idx, tag in enumerate(tag_map):
                if tag == actual_tag:
                    tag_idx = (50 - idx + 1)

            tag_idx = tag_idx * 100000

            if len(x.split("-")) == 3:
                year = x.split("-")[1]
                month_name = x.split("-")[2]
                tag_idx = tag_idx +  datetime.strptime(month_name, '%b').month + int(year) * 100
            else:
                year = x.split("-")[1]
                tag_idx = tag_idx + int(year) * 100 + 0

            # logger.critical("priority %s tag_idx %s", x, tag_idx)
            return tag_idx
        else:
            tag_idx = 1
            for idx, tag in enumerate(tag_map):
                if tag == x:
                    tag_idx = (50 - idx + 1)

            tag_idx = tag_idx * 100000

            # logger.critical("priority %s tag_idx %s", x, tag_idx)
            return tag_idx

    classify_list.sort(key=score_tag_idx, reverse=True)
    # for classify in classify_list:
    #     logger.critical("priority %s tag_idx %s", classify, score_tag_idx(classify))
        
    # logger.critical("classify list %s", classify_list)
    
    def getTitle(tag):
        
        
       
        job_profile_data_len = r_get("classify_" + tag + "_len", account_name, account_config)
        if job_profile_data_len is None:
            job_profile_data_len = 0
        else:
            job_profile_data_len = int(job_profile_data_len)

        if tag not in tag_map:
            if "Ex:" in tag:
                tag_map[tag] = tag
            elif "-" in tag:
                tags = tag.split("-")
                if tags[0] in tag_map:
                    tag_map[tag] = tag.replace(tags[0],tag_map[tags[0]])
            else:
                tag_map[tag] = tag.replace("Ex:", "Ex Job: ")

        title = tag_map[tag]
        return title, job_profile_data_len
    # for tag in tag_map.keys():

    for tag in classify_list:
        tag = tag.replace("classify_","")
        title, job_profile_data_len = getTitle(tag)
        if "-" not in title:
            response.append({
                    "active_status": True,
                    "assign_to_all_emails": False,
                    "count": job_profile_data_len,
                    "default": True,
                    "id": len(response),
                    "parent_id": "0",
                    "read": -1,
                    "roundDetails": [],
                    "sequence": 0,
                    "title": title,
                    "unread": -1,
                    "_id": len(response),
                    "key" : tag,
                    "children" : []
                    })

    for tag in classify_list:
        tag = tag.replace("classify_","")
        title, job_profile_data_len = getTitle(tag)
        if "-" in title:
            nest = title.split("-")
            parent = nest[0]
            for idx, resp in enumerate(response):
                if resp["title"] == parent:
                    children = resp["children"]
                    child_title = " ".join(nest[1:])
                    response[idx]["count"] = response[idx]["count"] + int(job_profile_data_len)
                    response[idx]["children"].append({
                        "active_status": True,
                        "assign_to_all_emails": False,
                        "count": job_profile_data_len,
                        "default": True,
                        "id": str(len(response)) + "-" + str(len(resp["children"])),
                        "parent_id": "0",
                        "read": -1,
                        "roundDetails": [],
                        "sequence": 0,
                        "title": child_title,
                        "unread": -1,
                        "_id": str(len(response)) + "-" + str(len(resp["children"])),
                        "key" : tag
                    })



    # return sorted(response, key=lambda x: x['count'], reverse=True)
    return response

def get_candidate_tags(account_name, account_config):
    # if account_name == "rocketrecruit":
    return get_candidate_tags_v2(account_name, account_config)
    

def indexAll(account_name, account_config):
    return ""
    r = connect_redis(account_name, account_config)

    logger.critical("index all called")
    data = r_get("full_data", account_name, account_config)
    if data:
        dataMap = json.loads(data)
        data = []
        for dkey in dataMap:
            data.append(dataMap[dkey])
        generateFilterMap("full_data",data, account_name, account_config)

    
    for key in r_scan_iter(account_name, account_config, match='*on_ai_data*',):
        # key = key.decode("utf-8")

        
        # basically delete the unique_cache_key below if job data changes
        if "on_ai_data" in key:
            logger.critical("cleaching cache %s", key)
            # r.delete(key)
                    
        if "_filter" in str(key):
            continue

        if "classify_" in str(key):
            data = r_get(key, account_name, account_config)
            dataMap = json.loads(data)
            data = []
            for dkey in dataMap:
                data.append(dataMap[dkey])
            key = str(key)
            generateFilterMap(key.replace("classify_",""),data, account_name, account_config)

        if "job_" in str(key):
            data = r_get(key, account_name, account_config)
            dataMap = json.loads(data)
            data = []
            for dkey in dataMap:
                data.append(dataMap[dkey])
            key = str(key)
            
            generateFilterMap(key.replace("job_",""),data, account_name, account_config)


def get_job_profile_data(mongoid, account_name, account_config, tag_id = None):
    db = initDB(account_name, account_config)
    r = connect_redis(account_name, account_config) 
    if not tag_id:
        ret = db.emailStored.find({"job_profile_id" : mongoid} , {"body": 0, "cvParsedInfo.debug": 0})
    else:
        ret = db.emailStored.find({"job_profile_id" : mongoid, "tag_id" : tag_id} , {"body": 0, "cvParsedInfo.debug": 0})

    job_profile_data = {}
    for row in ret:
        row["_id"] = str(row["_id"])
        job_profile_data[row["_id"]] = row

    r_set("job_fx_" + mongoid, json.dumps(job_profile_data, default=str), account_name, account_config)
    return job_profile_data

def get_classify_data(mongoid, page, limit, account_name, account_config):
    r = connect_redis(account_name, account_config) 
    db = initDB(account_name, account_config)
    if "NOT_ASSIGNED" in mongoid:
        
        if len(mongoid.split("-")) == 3:
                label = mongoid.split("-")[0]
                year = int(mongoid.split("-")[1])
                month_name = mongoid.split("-")[2]
                month = datetime.strptime(month_name, '%b').month
                start_date = datetime(year, month, 1, 0,0,0)
                end_date = datetime(year, month, monthrange(year, month)[1], 0,0,0)
                datecondition = {
                    "$gte" : start_date,
                    "$lte" : end_date,
                }
        elif len(mongoid.split("-")) == 2:
            label = mongoid.split("-")[0]
            year = int(mongoid.split("-")[1])
            start_date = datetime(year, 1, 1, 0,0,0)
            end_date = datetime(year, 12, 31, 0,0,0)
            datecondition = {
                "$gte" : start_date,
                "$lte" : end_date,
            }
        else:
            datecondition = {
                    "$gt" : datetime.now() - timedelta(days=15)
            }

        ret = db.emailStored.find(
            {
                "$or" : [
                    {"job_profile_id" : {"$exists":False}},
                    {"$expr": { "$eq": [ { "$strLenCP": "$job_profile_id" }, 0 ] } }
                ],
                "date" : datecondition,
                "ex_job_profile" : {"$exists":False}
            }, 
            {"body": 0, "cvParsedInfo.debug": 0})
        
        job_profile_data = {}
        for row in ret:
            row["_id"] = str(row["_id"])
            job_profile_data[row["_id"]] = row

        r_set("job_fx_" + mongoid, json.dumps(job_profile_data, default=str), account_name, account_config)
    else:
        if "-" in mongoid:
            if len(mongoid.split("-")) == 3:
                label = mongoid.split("-")[0]
                year = int(mongoid.split("-")[1])
                month_name = mongoid.split("-")[2]
                month = datetime.strptime(month_name, '%b').month
                start_date = datetime(year, month, 1, 0,0,0)
                end_date = datetime(year, month, monthrange(year, month)[1], 0,0,0)
            else:
                label = mongoid.split("-")[0]
                year = int(mongoid.split("-")[1])
                start_date = datetime(year, 1, 1, 0,0,0)
                end_date = datetime(year, 12, 31, 0,0,0)
        


            db = initDB(account_name, account_config)
            job_profile_data = {}
            if "Ex:" in label:
                ret = db.emailStored.find(
                    {
                        
                        "ex_job_profile.name" : label.replace("Ex:",""),
                        "date" : {
                            "$gte" : start_date,
                            "$lte" : end_date,
                        }
                    }, 
                    {"body": 0, "cvParsedInfo.debug": 0})
                for row in ret:
                    row["_id"] = str(row["_id"])
                    job_profile_data[row["_id"]] = row
            else:
                ret = db.emailStored.find(
                    {
                        
                        "candidateClassify.label" : label,
                        "date" : {
                            "$gte" : start_date,
                            "$lte" : end_date,
                        }
                    }, 
                    {"body": 0, "cvParsedInfo.debug": 0})
                for row in ret:
                    row["_id"] = str(row["_id"])
                    job_profile_data[row["_id"]] = row

            
        else:
            label = mongoid
            job_profile_data = {}
            db = initDB(account_name, account_config)
            if "Ex:" in label:
                
                ret = db.emailStored.find(
                    {
                        
                        "ex_job_profile.name" : label.replace("Ex:",""),
                    }, 
                    {"body": 0, "cvParsedInfo.debug": 0})
                for row in ret:
                    row["_id"] = str(row["_id"])
                    job_profile_data[row["_id"]] = row
            else:
                ret = {}
                if limit == -1:
                    ret = db.emailStored.find(
                        {
                            
                            "candidateClassify.label" : label,
                        }, 
                        {"body": 0, "cvParsedInfo.debug": 0})
                else:
                    ret = db.emailStored.find(
                        {
                            
                            "candidateClassify.label" : label,
                        }, 
                        {"body": 0, "cvParsedInfo.debug": 0}).sort("email_date", -1).limit(limit).skip(page*limit)

                for row in ret:
                    row["_id"] = str(row["_id"])
                    job_profile_data[row["_id"]] = row

        if job_profile_data:
            # r_set("job_fx_" + mongoid, json.dumps(job_profile_data, default=str), account_name, account_config)
            # not putting classify data in db
            pass
        else:
            job_profile_data = {}

    return job_profile_data
def fetch(mongoid, filter_type="job_profile" , tags = [], page = 0, limit = 25, on_ai_data = False, filter = {}, on_starred = False, on_conversation = False, on_highscore = False, on_un_parsed = False,on_is_read=False, on_is_un_read=False,on_is_note_added = False, on_calling_status = None, sortby = None, sortorder = None, account_name = "", account_config = {}):
    
    r = connect_redis(account_name, account_config) 
    

    page = int(page)
    limit = int(limit)

    logger.critical("page %s", page)
    logger.critical("limit %s", limit)
    logger.critical("send ai info %s", on_ai_data)
    logger.critical("filter %s", filter)
    logger.critical("starred %s", on_starred)
    logger.critical("conversation %s", on_conversation)
    logger.critical("high score %s", on_highscore)
    logger.critical("unparsed %s", on_un_parsed)

    logger.critical("is unread %s", on_is_un_read)
    logger.critical("is_read %s", on_is_read)
    logger.critical("on_is_note_added %s", on_is_note_added)
    logger.critical("on_calling_status %s", on_calling_status)

    logger.critical("tags %s",tags)
    logger.critical("len tags %s", len(tags))
    logger.critical("mongo id %s", mongoid)
    logger.critical("filter type %s", filter_type)
    logger.critical("sort by %s", sortby)
    logger.critical("sort order %s", sortorder)
    candidate_map = {}

    candidate_filter_map = {}

    
    tag_map = {}
    tag_count_map = {}


    if filter_type == "job_profile":
        job_profile_data = r_get("job_fx_" + mongoid, account_name, account_config)
        job_profile_data = json.loads(job_profile_data)
        # logger.critical("length of job profile data %s", len(job_profile_data))
    else:
        job_profile_data = r_get("classify_fx_" + mongoid, account_name, account_config)
        job_profile_data = json.loads(job_profile_data)
        # logger.critical("length of job profile data %s", len(job_profile_data))
        # job_profile_data = False

    

    if job_profile_data  and use_unique_cache_feature:
        if job_profile_data is None:
            job_profile_data = {}
        elif isinstance(job_profile_data, list):
            job_profile_data = {}
        else:
            logger.critical("using cached data")
    else:
        logger.critical("keys not found unable to use cached data")
        job_profile_data = None
        if filter_type == "job_profile":
            job_profile_data = get_job_profile_data(mongoid, account_name, account_config)
        else:
            job_profile_data = get_classify_data(mongoid, page, limit, account_name, account_config)
        # logger.critical("length of job profile data %s label %s start_date %s end_date %s", len(job_profile_data), label, start_date, end_date)

        
    is_option = False
    


    # logger.critical("length of job profile data %s", len(job_profile_data))
    if on_is_un_read:
        is_option = True
        unread_job_profile_data = {}

        for key in job_profile_data:
            item = job_profile_data[key]
            if "unread" in item:
                if item["unread"]:
                    unread_job_profile_data[key] = item

        job_profile_data = unread_job_profile_data

    if on_is_read:
        is_option = True
        unread_job_profile_data = {}

        for key in job_profile_data:
            item = job_profile_data[key]
            if "unread" in item:
                if not item["unread"]:
                    unread_job_profile_data[key] = item

        job_profile_data = unread_job_profile_data

    if on_is_note_added:
        is_option = True
        unread_job_profile_data = {}
        for key in job_profile_data:
            item = job_profile_data[key]
            if "notes" in item:
                if len(item["notes"]) > 0:
                    unread_job_profile_data[key] = item

        job_profile_data = unread_job_profile_data

    if on_starred:
        is_option = True
        starred_job_profile_data = {}

        for key in job_profile_data:
            item = job_profile_data[key]
            if "candidate_star" in item:
                if len(item["candidate_star"]) > 0:
                    starred_job_profile_data[key] = item

        job_profile_data = starred_job_profile_data
    
    if on_calling_status:
        is_option = True
        starred_job_profile_data = {}

        for key in job_profile_data:
            item = job_profile_data[key]
            if "callingStatus" in item:
                if item["callingStatus"] == on_calling_status:
                    starred_job_profile_data[key] = item

        job_profile_data = starred_job_profile_data


    if on_conversation:
        is_option = True
        conversion_job_profile_data = {}

        for key in job_profile_data:
            item = job_profile_data[key]
            if "conversation" in item:
                if item["conversation"]:
                    if "unreadConversations" in item:
                        if item["unreadConversations"] > 0:
                            conversion_job_profile_data[key] = item

        job_profile_data = conversion_job_profile_data

    if on_highscore:
        is_option = True
        conversion_job_profile_data = {}

        for key in job_profile_data:
            item = job_profile_data[key]
            if "cvParsedInfo" in item:
                if "candidate_score" in item["cvParsedInfo"]:
                    if item["cvParsedInfo"]["candidate_score"] > 6:
                        conversion_job_profile_data[key] = item

        job_profile_data = conversion_job_profile_data

    if on_un_parsed:
        is_option = True
        unparsed_job_profile_data = {}

        for key in job_profile_data:
            item = job_profile_data[key]
            if "cvParsedAI" not in item:
                if "attachment" in item:
                    if len(item["attachment"]) > 0:
                        unparsed_job_profile_data[key] = item

            

        job_profile_data = unparsed_job_profile_data

    if len(tags) > 0:
        logger.critical("sorting..")

        if filter_type == "job_profile":

            tag_idx_sort_map = {}
            def custom_sort(item):
                
                if "sequence" not in list(item[1].keys()):
                    logger.critical("-1")
                    return -1
                
                if item[1]["tag_id"] not in tag_idx_sort_map:
                    tag_idx_sort_map[item[1]["tag_id"]] = (len(tag_idx_sort_map) + 1) * 100000000
                    # need to have sorting based on tags instead of global so need to bring numbers in a range per tag
                
                sequence = tag_idx_sort_map[item[1]["tag_id"]] + float(item[1]["sequence"])

                # if item[1]["job_profile_id"] == "5ea68456a588f5003ac3db32":
                #     logger.critical("seqqqqq %s tag id %s", sequence, item[1]["tag_id"])
                
                return sequence * -1


            job_profile_data = {k: v for k, v in sorted(job_profile_data.items(), key=custom_sort)}
        else:
            # if filter_type != 'full':
            def custom_sort_date(item):
                if "email_timestamp" in item[1]:    
                    # 2020-06-17 15:12:44.156000
                    # return datetime.strptime(item[1]["created_at"], '%Y-%m-%d %H:%M:%S.%f')
                    # return datetime.utcfromtimestamp(email_timestamp)
                    if isinstance(item[1]["email_timestamp"], int):
                        return ""
                    else:
                        return item[1]["email_timestamp"]
                else:
                    return ""

            job_profile_data = {k: v for k, v in sorted(job_profile_data.items(), key=custom_sort_date,reverse=True)}
        
        logger.critical("sorted..")

    else:
        def custom_sort_date(item):
            if "email_timestamp" in item[1]:    
                # 2020-06-17 15:12:44.156000
                # return datetime.strptime(item[1]["created_at"], '%Y-%m-%d %H:%M:%S.%f')
                if isinstance(item[1]["email_timestamp"], int):
                    return ""
                else:
                    return item[1]["email_timestamp"]

            else:
                return ""

        def custom_sort(item):
                    
            if "sequence" not in list(item[1].keys()):
                logger.critical("-1")
                return -1
            
            return float(item[1]["sequence"])  * -1
        
        def sort_score(item):
                    
            if "cvParsedInfo" not in list(item[1].keys()):
                logger.critical("-1")
                return -1
            
            if "candidateScore" not in item[1]["cvParsedInfo"]:
                logger.critical("-1")
                return -1
            
            return float(item[1]["cvParsedInfo"])  * -1

        if filter_type == "job_profile":    
            


            # print(job_profile_data)
            if sortby == None:
                job_profile_data = {k: v for k, v in sorted(job_profile_data.items(), key=custom_sort)}
            elif sortby == "date":
                if sortorder == 1:
                    job_profile_data = {k: v for k, v in sorted(job_profile_data.items(), key=custom_sort_date,reverse=True)}
                else:
                    job_profile_data = {k: v for k, v in sorted(job_profile_data.items(), key=custom_sort_date,reverse=False)}

            elif sortby == "score":
                if sortorder == 1:
                    job_profile_data = {k: v for k, v in sorted(job_profile_data.items(), key=sort_score,reverse=True)}
                else:
                    job_profile_data = {k: v for k, v in sorted(job_profile_data.items(), key=sort_score,reverse=False)}
            
            else:
                job_profile_data = {k: v for k, v in sorted(job_profile_data.items(), key=custom_sort)}
            
        else:
            job_profile_data = {k: v for k, v in sorted(job_profile_data.items(), key=custom_sort_date,reverse=True)}

    tagged_job_profile_data = {}
    for id in job_profile_data:
        row = job_profile_data[id]

        if "tag_id" not in row:
            row["tag_id"] = ""

        if filter_type == "job_profile":    
            tag_id = row["tag_id"]
        else:
            tag_id = mongoid

        

        if len(tag_id) == 0:
            continue

        if tag_id not in tag_map:
            tag_map[tag_id] = []
            tag_count_map[tag_id] = 0
        
        tag_count_map[tag_id] += 1
        tag_map[tag_id].append(row["_id"])


        if tag_id in tags:
            tagged_job_profile_data[id] = row
        
            
        # if "cvParsedInfo" in row:
        #     del row["cvParsedInfo"]


        # candidate_map[row["_id"]] = row

    if len(tags) > 0:
        job_profile_data = tagged_job_profile_data

        logger.critical("tag count map")
        logger.critical(tag_count_map)
    
    if len(tags) > 0:   
        
        # {
        #     "filter" : {
        #         "edu_filter" : ["M.D"],
        #         "work_filter" : ["other", "internship"]
        #     }
        # }

        paged_candidate_map = {}
        for idx, child_id in  enumerate(job_profile_data):
            if idx >= page * limit and idx < limit * (page + 1):
                doc = job_profile_data[child_id]
                paged_candidate_map[child_id] = doc


        filter_tag_children = {}
        
        
        if len(tags) == 1:
            logger.critical("tag id %s", tags[0])
            ret =  r_get(tags[0] + "_filter_children", account_name, account_config)
            if ret is not None:
                ret = json.loads(ret)
            else:
                ret = {}
        else:
            logger.critical("tag id %s", ",".join(tags))
            ret =  r_get(",".join(tags) + "_filter_children", account_name, account_config)
            if ret is not None:
                ret = json.loads(ret)
            else:
                ret = {}
            
        if len(filter) > 0:
            logger.critical("filter")
            logger.critical(json.dumps(filter, indent=True))
            logger.critical(list(filter.keys()))
            for key in ret:
                logger.critical("key %s", key)
                if key not in list(filter.keys()):
                    continue 

                
                logger.critical("key found in filter %s" , key)
                for rangekey in ret[key]:
                    logger.critical(rangekey)
                    if isinstance(filter[key], bool):
                        continue 
                    if rangekey not in filter[key]:
                        continue

                    logger.critical("range key %s", rangekey)

                    range = ret[key][rangekey]
                    if "children" not in range:
                        range["children"]  = []

                    children = range["children"]

                    logger.critical("children %s", children)
                    newChildren = []
                    for child in children:
                        if isinstance(child, dict):
                            child_id = list(child.keys())[0]
                        else:
                            child_id = child

                        logger.critical("child_id %s", child_id)
                        if child_id in job_profile_data:
                            newChildren.append(child)
                            filter_tag_children[child_id] = job_profile_data[child_id]
                        else:
                            logger.critical("doesnt exist")
                            pass
                    
                    # logger.critical("new children %s", newChildren)
                    ret[key][rangekey]["tag_count"] = len(newChildren)
                    ret[key][rangekey]["children"] = newChildren
                    if "merge" in ret[key][rangekey]:
                        del ret[key][rangekey]["merge"]
            
            # logger.critical("filter data %s", len(filter_tag_children))
            job_profile_data = filter_tag_children

        logger.info("is_option %s", is_option)
        total_candidate_len = len(job_profile_data)
        paged_candidate_map = {}
        for idx, child_id in  enumerate(job_profile_data):
            if idx >= page * limit and idx < limit * (page + 1):
                doc = job_profile_data[child_id]
                if len(filter) == 0 and not is_option:
                    if not on_ai_data:
                        if "pipeline" in doc:
                            del doc["pipeline"]
                        if "candidateClassify" in doc:
                            del doc["candidateClassify"]
                        if "attachment" in doc:
                            del doc["attachment"]
                        if "addSearch" in doc:
                            del doc["addSearch"]
                        if "answered" in doc:
                            del doc["answered"]
                        if "cvText" in doc:
                            del doc["cvText"]
                        if "cvParsedInfo" in doc:
                            del doc["cvParsedInfo"]

                        
                    else:
                    
                        if "cvParsedInfo" in doc:
                            cvParsedInfo = doc["cvParsedInfo"]
                            if "debug" in cvParsedInfo:
                                del cvParsedInfo["debug"]
                            
                            if "complete_section_match_map" in cvParsedInfo:
                                del cvParsedInfo["complete_section_match_map"]

                            if "qa_parse_resume" in cvParsedInfo:
                                del cvParsedInfo["qa_parse_resume"]

                            if "page_contents" in cvParsedInfo:
                                del cvParsedInfo["page_contents"]

                            if "qa_fast_search_space" in cvParsedInfo:
                                del cvParsedInfo["qa_fast_search_space"]

                            # if "newCompressedStructuredContent" in cvParsedInfo:
                            #     del cvParsedInfo["newCompressedStructuredContent"]
                            
                        else:
                            cvParsedInfo = {}

                        doc = {
                            "cvParsedInfo" : cvParsedInfo
                        }
                    
                paged_candidate_map[child_id] = doc


        
        
        
        
        logger.critical("sending response..")

        response = json.dumps({
            "filter" : {}, # ret temp code to comment filters as its coming from another api only now 
            "candidate_map" : paged_candidate_map,
            "candidate_len" : len(paged_candidate_map),
            "total_candidate_len":total_candidate_len,
            "tag_count_map" : tag_count_map
        }, default=str)

        return response
    else:
        paged_tag_map = {}
        def custom_tag_sort(item):
            if "sequence" not in item:
                return -1 

            # logger.critical(float(item[1]["sequence"]))
            return float(item["sequence"])  * 1

        logger.critical("generating response..")
        for tag in tag_map:
            paged_tag_map[tag] = {
                "data" : [],
                'read' : 0,
                'unread' : 0
            }
            tag_map[tag]  = sorted(tag_map[tag] , key=custom_tag_sort, reverse=False)

            for idx, child_id in enumerate(tag_map[tag]):
                doc = job_profile_data[child_id]
                if "unread" in doc and doc["unread"]:
                    paged_tag_map[tag]["unread"] += 1
                else:
                    paged_tag_map[tag]["read"] += 1

                if idx >= page * limit and idx < limit * (page + 1):
                
                    if not on_ai_data:
                        if "pipeline" in doc:
                            del doc["pipeline"]
                        if "candidateClassify" in doc:
                            del doc["candidateClassify"]
                        if "attachment" in doc:
                            del doc["attachment"]
                        if "addSearch" in doc:
                            del doc["addSearch"]
                        if "answered" in doc:
                            del doc["answered"]
                        if "cvText" in doc:
                            del doc["cvText"]
                        if "cvParsedInfo" in doc:
                            del doc["cvParsedInfo"]

                        if "debug" in doc:
                            del doc["debug"]

                    else:
                    
                        if "cvParsedInfo" in doc:
                            cvParsedInfo = doc["cvParsedInfo"]
                        else:
                            cvParsedInfo = {}

                        doc = {
                            "cvParsedInfo" : cvParsedInfo
                        }
                    
                    paged_tag_map[tag]["data"].append(doc)

                


        logger.critical("response completed..")
        response =  json.dumps(paged_tag_map, default=str)

        if filter_type != "job_profile":
            final_data = []
            final_read = 0
            final_unread = 0
            for tag_id in paged_tag_map:
                data = paged_tag_map[tag_id]["data"]
                read = paged_tag_map[tag_id]["read"]
                unread = paged_tag_map[tag_id]["unread"]

                final_data.extend(data)
                final_read += read
                final_unread += unread

            response = {
                "data": final_data,
                "read" : final_read,
                "unread" : final_unread
            }
            response =  json.dumps(response, default=str)

        return response
            

def clear_unique_cache(job_profile_id, tag_id, account_name = "", account_config = {}):
    pass
    
def get_index(tag_id, job_profile_id, account_name, account_config):
    r = connect_redis(account_name, account_config)
    logger.critical("checking index %s", tag_id)
    if r_exists(tag_id + "_filter", account_name, account_config) and False:
        ret =  r_get(tag_id + "_filter", account_name, account_config)
    else:
        if job_profile_id:
            index(job_profile_id, tag_id, "job_profile", account_name, account_config)
            return r_get(tag_id + "_filter", account_name, account_config)
        else:
            return "-1"

    return ret

def index(mongoid, tag_id = None, filter_type="job_profile", account_name = "", account_config = {}):
    data = [] 


    logger.critical("index called %s", mongoid)
    r = connect_redis(account_name, account_config)

    if filter_type == "full_data":
        logger.critical("full data is not implemented anymore")
        return {}
            
    elif filter_type == "job_profile":
        data = r_get("job_fx_" + mongoid, account_name, account_config)
        
 
        if data and json.loads(data) and use_unique_cache_feature:         
            dataMap = json.loads(data)
        else:
            dataMap = get_job_profile_data(mongoid, account_name, account_config)

        logger.critical("data map %s", len(dataMap))
        data = []
        tag_data_map = {}
        for dkey in dataMap:
            data.append(dataMap[dkey])
            if dataMap[dkey]["tag_id"] not in tag_data_map:
                tag_data_map[dataMap[dkey]["tag_id"]] = []
            
            tag_data_map[dataMap[dkey]["tag_id"]].append(dataMap[dkey])

        key = mongoid

        if tag_id and "," in tag_id:
            new_data = []
            array_tag_id = tag_id.split(",")
            for x_tag_id in tag_data_map:
                if x_tag_id in array_tag_id:
                    new_data.extend(tag_data_map[x_tag_id])

            logger.critical("data len %s for tag id %s" , len(new_data), tag_id)
            generateFilterMap(tag_id, new_data, account_name, account_config)
            return {}



        for x_tag_id in tag_data_map:
            if tag_id:
                if x_tag_id != tag_id:
                    continue

            logger.critical("data len %s for tag id %s" , len(tag_data_map[tag_id]), x_tag_id)
            generateFilterMap(x_tag_id, tag_data_map[x_tag_id], account_name, account_config)
    

        logger.critical("idex completed job profile data")
        return {}



        

    elif filter_type == "candidate":
        data = r_get("classify_fx_" + mongoid, account_name, account_config)
        if data and json.loads(data) and use_unique_cache_feature:
            dataMap = json.loads(data)
        else:
            dataMap = get_classify_data(mongoid, 0, -1, account_name, account_config)

        
        

        data = []
        for dkey in dataMap:
            data.append(dataMap[dkey])

        key = mongoid

        

        logger.critical("data len %s" , len(data))
        generateFilterMap(key, data, account_name, account_config)
        logger.critical("idex completed candidate data")
        return {}

    
def generateFilterMap(key, data, account_name, account_config):


    logger.critical("generating filter .......................")
    r = connect_redis(account_name, account_config)
    key = str(key)
    wrkExpList = []
    gpeList = []

    wrkExpIdxMap = {}
    gpeIdxMap = {}
    exp_map = {}
    education_map = {}
    passout_map = {}
    gender_map = {}
    dob_map = {}

    is_starred = {"count" : 0, "children": []}
    is_unread = {"count" : 0, "children": []}
    is_read = {"count" : 0, "children": []}
    is_highscore = {}
    is_note_added = {"count" : 0, "children": []}
    call_status = {}
    conversion_pending = {"count" : 0, "children": []}

    for row in data:
        if "notes" in row:
            if len(row["notes"]) > 0:
                is_note_added["count"] += 1
                is_note_added["children"].append(str(row["_id"]))

        if "candidate_star" in row:
            if len(row["candidate_star"]) > 0:
                is_starred["count"] += 1
                is_starred["children"].append(str(row["_id"]))
        
        if "unread" in row:
            if row["unread"]:
                is_unread["count"] += 1
                is_unread["children"].append(str(row["_id"]))
            else:
                is_read["count"] += 1
                is_read["children"].append(str(row["_id"]))

        if "cvParsedInfo" in row:
            if "candidate_score" in row["cvParsedInfo"]:
                score = row["cvParsedInfo"]["candidate_score"]
                if score > 5:
                    if score < 7.5:
                        if "score_5_75" not in is_highscore:
                            is_highscore["score_5_75"] = {"count" : 0, "children": [],"display": f"Score 5 - 7.5"}

                        is_highscore["score_5_75"]["count"] += 1
                        is_highscore["score_5_75"]["children"].append(str(row["_id"]))
                    else:
                        if "score_75_10" not in is_highscore:
                            is_highscore["score_75_10"] = {"count" : 0, "children": [],"display": f"Score 7.5 - 10"}

                        is_highscore["score_75_10"]["count"] += 1
                        is_highscore["score_75_10"]["children"].append(str(row["_id"]))


        if "callingStatus" in row:
            callingStatus = row["callingStatus"]
            if callingStatus not in call_status:
                call_status[callingStatus] = {"count" : 0, "children": []}
            
            call_status[callingStatus]["count"] += 1
            call_status[callingStatus]["children"].append(str(row["_id"]))

        if "conversation" in row:
            if row['conversation']:
                conversion_pending["count"] += 1
                conversion_pending["children"].append(str(row["_id"]))

        if "cvParsedInfo" in row and  "finalEntity" in row["cvParsedInfo"]:  

            if "ExperianceYears" in row["cvParsedInfo"]["finalEntity"]:
                ExperianceYears = row["cvParsedInfo"]["finalEntity"]["ExperianceYears"]
                # print(ExperianceYears["obj"])

                days, _, _ =  parse_experiance_years(ExperianceYears["obj"])
                exp_map[str(row["_id"])] = days

            EducationDegree = []
            if "EducationDegree" in row["cvParsedInfo"]["finalEntity"]:

                if "EducationDegree" in row["cvParsedInfo"]["finalEntity"]:
                    EducationDegree.append(row["cvParsedInfo"]["finalEntity"]["EducationDegree"]["obj"])
                
            if "education"  in row["cvParsedInfo"]["finalEntity"]:
                education = row["cvParsedInfo"]["finalEntity"]["education"]
                for edu in education:
                    for e in edu:
                        if "EducationDegree" in e:
                            EducationDegree.append(e["EducationDegree"])

            if len(EducationDegree) > 0:
                education_map[str(row["_id"])] = EducationDegree

            if "wrkExp" in row["cvParsedInfo"]["finalEntity"]:
                wrkExp = row["cvParsedInfo"]["finalEntity"]["wrkExp"]
                if wrkExp:
                    for ww in wrkExp:
                        for w in ww:
                            if "Designation" in w:
                                wrkExpList.append(w["Designation"])
                                wrkExpIdxMap[len(wrkExpList) - 1] = str(row["_id"])

            if "GPE" in row["cvParsedInfo"]["finalEntity"]:
                GPE = row["cvParsedInfo"]["finalEntity"]["GPE"]
                if GPE:
                    gpeList.append(GPE["obj"])
                    gpeIdxMap[len(gpeList) - 1] = str(row["_id"])

            
            if "gender" in row["cvParsedInfo"]["finalEntity"]:
                gender = row["cvParsedInfo"]["finalEntity"]["gender"][0].lower()
                if len(gender) > 0:
                    gender_map[str(row["_id"])] = gender

            if "answer_map" in row["cvParsedInfo"]:
                answer_map = row["cvParsedInfo"]["answer_map"]
                if "education_year" in answer_map:
                    if "error" not in answer_map["education_year"]:
                        passout_year = answer_map["education_year"]["answer"]
                        if len(passout_year) > 0:
                            passout_map[str(row["_id"])] = passout_year

            dob_str = ""
            if "answer_map" in row["cvParsedInfo"]:
                answer_map = row["cvParsedInfo"]["answer_map"]
                if "personal_dob" in answer_map:
                    if "error" not in answer_map["personal_dob"]:
                        dob_str = answer_map["personal_dob"]["answer"]
                        dob_map[str(row["_id"])] = dob_str
                
            
            if len(dob_str) == 0:
                if "finalEntity" in row["cvParsedInfo"]:
                    if "DOB" in row["cvParsedInfo"]["finalEntity"]:
                        dob_str = row["cvParsedInfo"]["finalEntity"]["DOB"]["obj"]
                        dob_map[str(row["_id"])] = dob_str
                        

    exp_filter = getExperianceRange(exp_map)
    edu_filter = getEducationFilters(education_map)
    passout_filter = getPassoutYearFilters(passout_map)
    work_filter = designation(wrkExpList, wrkExpIdxMap)
    gpe_filter = location(gpeList,gpeIdxMap)
    gender_filter = getGenderFilter(gender_map)
    dob_filter = get_dob_filter(dob_map)

    r_set(key + "_filter_children" , json.dumps({
        "exp_filter" : exp_filter,
        "edu_filter" : edu_filter,
        "work_filter" : work_filter,
        "gpe_filter" : gpe_filter,
        "passout_filter" : passout_filter,
        "gender_filter" : gender_filter,
        "dob_filter" : dob_filter,
        "is_starred" : is_starred,
        "is_unread" : is_unread,
        "is_read" : is_read,
        "is_highscore" : is_highscore,
        "is_note_added" : is_note_added,
        "call_status" : call_status,
        "conversion_pending" : conversion_pending
    }), account_name, account_config)

    del is_starred["children"]
    del is_unread["children"]
    del is_note_added["children"]
    del is_read["children"]
    del conversion_pending["children"]

    for key2 in is_highscore:
        # edu_filter[key]["children"] = []
        del is_highscore[key2]["children"]

    for key2 in call_status:
        # edu_filter[key]["children"] = []
        del call_status[key2]["children"]
    

    for key2 in exp_filter:
        # exp_filter[key]["children"] = []
        if "children" in exp_filter[key2]:
            del exp_filter[key2]["children"]
        if "sub_range" in exp_filter[key2]:
            for key3 in exp_filter[key2]["sub_range"]:
                if "children" in exp_filter[key2]["sub_range"][key3]:
                    del exp_filter[key2]["sub_range"][key3]["children"]

    for key2 in edu_filter:
        # edu_filter[key]["children"] = []
        del edu_filter[key2]["children"]

    for key2 in work_filter:
        # work_filter[key]["children"] = []
        del work_filter[key2]["children"]
        
    for key2 in gpe_filter:
        # gpe_filter[key]["children"] = []
        del gpe_filter[key2]["children"]

    for key2 in gender_filter:
        # gender_filter[key]["children"] = []
        del gender_filter[key2]["children"]

    for key2 in passout_filter:
        # passout_filter[key]["children"] = []
        del passout_filter[key2]["children"]

    for key2 in dob_filter:
        # dob_filter[key]["children"] = []
        del dob_filter[key2]["children"]
    

    logger.critical("generating filter completed %s", key)
    # print(edu_filter)
    r_set(key + "_filter" , json.dumps({
        "exp_filter" : exp_filter,
        "edu_filter" : edu_filter,
        "work_filter" : work_filter,
        "gpe_filter" : gpe_filter,
        "passout_filter" : passout_filter,
        "gender_filter" : gender_filter,
        "dob_filter" : dob_filter,
        "is_starred" : is_starred,
        "is_unread" : is_unread,
        "is_read" : is_read,
        "is_highscore" : is_highscore,
        "is_note_added" : is_note_added,
        "call_status" : call_status,
        "conversion_pending" : conversion_pending
    }), account_name, account_config)


    logger.critical("completed for key %s", key)

    return {"key" : key}