from app.logging import logger
from pymongo import MongoClient

from app.filter.util import parse_experiance_years, matchCourse, designation, location, getExperianceRange, getEducationFilters

import os
import redis
import json

from threading import Thread

from app.filter.util import getCourseDict
from datetime import datetime

from app.account import connect_redis

import requests
import hashlib   

def get_speedup_api(redisKey, url, payload, access_token, account_name, account_config):

    
    r = connect_redis(account_name, account_config)
    try:
        if len(payload) == 0:
            logger.info("get request to %s", url)
            data = requests.get(url + "?accessToken=" + access_token)
            data = data.json()
            data = json.dumps(data)
        else:
            logger.info("post request to %s with payload %s", url, payload)
            data = requests.post(url + "?accessToken=" + access_token , data = payload)
            data = data.json()
            data = json.dumps(data)
        
        logger.info("updating redis data for get speed up api")
        r.set(redisKey, data , ex=1 * 60 * 60) #expire in 1hr automatic
        return data
    except Exception as e:
        logger.critical("error in api %s %s", url, str(e))
        return json.dumps("error" + str(e))
    

    

def general_api_speed_up(url, payload, access_token, account_name, account_config):

    redisKey = "jb_" + hashlib.md5(  (url + json.dumps(payload)).encode('utf-8')  ).hexdigest()
    r = connect_redis(account_name, account_config)
    if r.exists(redisKey):
        logger.info("speed up data returned from redis %s", redisKey)
        t = Thread(target = get_speedup_api, args=(redisKey, url, payload, access_token, account_name, account_config))
        t.start()
        return r.get(redisKey)
    
    data = get_speedup_api(redisKey, url, payload, access_token, account_name, account_config)
    return data


# def get_job_overview(url, tag_id, access_token, redisKey , r):
#     url = url + "tag/" + tag_id + "?accessToken=" + access_token
#     data = requests.get(url)
#     data = data.json()
#     data = json.dumps(data)
#     r.set(redisKey, data , ex=1 * 60 * 60) #expire in 1hr automatic
#     logger.info("updated job overview redis key %s", redisKey)

#     return data

# def syncTagData(tag_id, url, access_token, account_name, account_config):
#     r = connect_redis(account_name, account_config)

#     if url[-1] != "/":
#         url = url + "/"

#     redisKey = "jb_" + tag_id + ''.join(e for e in url if e.isalnum())

#     if r.exists(redisKey):
#         logger.info("job overview data returned from redis %s", redisKey)
#         t = Thread(target = get_job_overview, args=(url, tag_id, access_token, redisKey , r))
#         t.start()
#         return r.get(redisKey)
    
#     data = get_job_overview(url, tag_id, access_token, redisKey , r)
#     return data


    


unique_cache_key_list = []
use_unique_cache_feature = True
use_unique_cache_only_for_classify_data = True
use_unique_cache_only_for_ai_data = True

def get_candidate_tags(account_name, account_config):
    # tags = ["TeachingEducation", "HRRecruitment", "accounts", "Sales", "legal", "softwaredevelopment", "marketing", "customerservice"]
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
    if r.exists("classify_list"):
        classify_list = r.get("classify_list")
        classify_list = json.loads(classify_list)
    

    # for tag in tag_map.keys():
    for tag in classify_list:

        tag = tag.replace("classify_","")
        
        job_profile_data = r.get("classify_" + tag)      
        if not job_profile_data:
            job_profile_data_len = 0
        else:
            job_profile_data_len = r.get("classify_" + tag + "_len")
            if job_profile_data_len is None:
                job_profile_data_len = 0
            else:
                job_profile_data_len = int(job_profile_data_len)

        if tag not in tag_map:
            if "Ex-" in tag:
                tag_map[tag] = tag
            else:
                tag_map[tag] = tag.replace("Ex-", "Ex Job: ")
    
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
                "title": tag_map[tag],
                "unread": -1,
                "_id": len(response),
                "key" : tag
                })

    return sorted(response, key=lambda x: x['count'], reverse=True)


def indexAll(account_name, account_config):
    global unique_cache_key_list
    r = connect_redis(account_name, account_config)

    logger.info("index all called")
    data = r.get("full_data")
    if data:
        dataMap = json.loads(data)
        data = []
        for dkey in dataMap:
            data.append(dataMap[dkey])
        generateFilterMap("full_data",data, account_name, account_config)

    
    unique_cache_key_list = []
    for key in r.scan_iter(match='*on_ai_data*',):
        # key = key.decode("utf-8")

        
        # basically delete the unique_cache_key below if job data changes
        if "on_ai_data" in key:
            logger.info("cleaching cache %s", key)
            r.delete(key)
                    
        if "_filter" in str(key):
            continue

        if "classify_" in str(key):
            data = r.get(key)
            dataMap = json.loads(data)
            data = []
            for dkey in dataMap:
                data.append(dataMap[dkey])
            key = str(key)
            generateFilterMap(key.replace("classify_",""),data, account_name, account_config)

        if "job_" in str(key):
            data = r.get(key)
            dataMap = json.loads(data)
            data = []
            for dkey in dataMap:
                data.append(dataMap[dkey])
            key = str(key)
            
            generateFilterMap(key.replace("job_",""),data, account_name, account_config)


def fetch(mongoid, filter_type="job_profile" , tags = [], page = 0, limit = 25, on_ai_data = False, filter = {}, on_starred = False, account_name = "", account_config = {}):
    global unique_cache_key_list
    
    r = connect_redis(account_name, account_config)    

    # if filter_type == "full_data":
    #     ret = r.get("full_data_filter")
    # else:
    #     logger.info("fetching for %s", mongoid)
    #     ret =  r.get(mongoid + "_filter")

    # # logger.info("filter from redis %s", ret)
        
    # if ret is None:
    #     # for debugging
    #     # for key in r.scan_iter():
    #     #     if "job_" in key or "classify_" in key:
    #     #         logger.info("key found %s", key)

    #     return json.dumps({})
    # else:


    unique_cache_key = account_name +"_job_" + mongoid + "filter_type_" + filter_type + "page_" + str(page) + "limit_" + str(limit) + "on_ai_data_" + str(on_ai_data) + "tags_" + str(hash(str(tags))) + "on_starred_" + str(on_starred)

    # to take this one level up. we will store all function params and call function again internally when cache is cleared

    # r.set(unique_cache_key + "_func", json.dumps({
    #     mongoid, 
    #     filter_type , 
    #     tags, 
    #     page, 
    #     limit, 
    #     on_ai_data,
    #     filter, 
    #     account_name, 
    #     account_config
    # }))


    cache_data = r.get(unique_cache_key)
    if len(filter) == 0:
        if cache_data is not None and use_unique_cache_feature:
            if use_unique_cache_only_for_ai_data:
                if on_ai_data:
                    logger.info("returning cached data %s", unique_cache_key)
                    unique_cache_key_list.append(unique_cache_key)
                    unique_cache_key_list = list(set(unique_cache_key_list))
                    return cache_data    
                else:
                    pass
            
            elif use_unique_cache_only_for_classify_data:
                if "classify_" in filter_type:
                    logger.info("returning cached data %s", unique_cache_key)
                    unique_cache_key_list.append(unique_cache_key)
                    unique_cache_key_list = list(set(unique_cache_key_list))
                    return cache_data    
                else:
                    pass

            else:
                logger.info("returning cached data %s", unique_cache_key)
                unique_cache_key_list.append(unique_cache_key)
                unique_cache_key_list = list(set(unique_cache_key_list))
                return cache_data


    page = int(page)
    limit = int(limit)

    logger.info("page %s", page)
    logger.info("limit %s", limit)
    logger.info("send ai info %s", on_ai_data)
    logger.info("filter %s", filter)
    logger.info("starred %s", on_starred)
    logger.info("tags %s",tags)
    logger.info("len tags %s", len(tags))
    logger.info("mongo id %s", mongoid)
    logger.info("filter type %s", filter_type)
    candidate_map = {}

    candidate_filter_map = {}

    
    tag_map = {}
    tag_count_map = {}
    

    if filter_type == "job_profile":
        job_profile_data = r.get("job_" + mongoid)
    else:
        job_profile_data = r.get("classify_" + mongoid)

    
    if job_profile_data:
        job_profile_data = json.loads(job_profile_data)
        if job_profile_data is None:
            job_profile_data = {}
        if isinstance(job_profile_data, list):
            job_profile_data = {}
    else:
        job_profile_data = {}   

    logger.info("length of job profile data %s", len(job_profile_data))

    if on_starred:
        starred_job_profile_data = {}

        for key in job_profile_data:
            item = job_profile_data[key]
            if "candidate_star" in item:
                if len(item["candidate_star"]) > 0:
                    starred_job_profile_data[key] = item

        job_profile_data = starred_job_profile_data
    

    if len(tags) > 0:
        logger.info("sorting..")

        if filter_type == "job_profile":

            tag_idx_sort_map = {}
            def custom_sort(item):
                
                if "sequence" not in list(item[1].keys()):
                    logger.info("-1")
                    return -1
                
                if item[1]["tag_id"] not in tag_idx_sort_map:
                    tag_idx_sort_map[item[1]["tag_id"]] = (len(tag_idx_sort_map) + 1) * 100000000
                    # need to have sorting based on tags instead of global so need to bring numbers in a range per tag
                
                sequence = tag_idx_sort_map[item[1]["tag_id"]] + float(item[1]["sequence"])

                # if item[1]["job_profile_id"] == "5ea68456a588f5003ac3db32":
                #     logger.info("seqqqqq %s tag id %s", sequence, item[1]["tag_id"])
                
                return sequence * 1


            job_profile_data = {k: v for k, v in sorted(job_profile_data.items(), key=custom_sort)}
        else:
            # if filter_type != 'full':
            def custom_sort_date(item):
                if "created_at" in item[1]:    
                    # 2020-06-17 15:12:44.156000
                    return datetime.strptime(item[1]["created_at"], '%Y-%m-%d %H:%M:%S.%f')
                else:
                    return -1

            job_profile_data = {k: v for k, v in sorted(job_profile_data.items(), key=custom_sort_date)}
            
        
        logger.info("sorted..")

    else:
        if filter_type == "job_profile":    
            def custom_sort(item):
                    
                if "sequence" not in list(item[1].keys()):
                    logger.info("-1")
                    return -1
                
                # logger.info(float(item[1]["sequence"]))

                return float(item[1]["sequence"])  * 1
                # return (item[1]["email_timestamp"]) * -1


            # print(job_profile_data)
            job_profile_data = {k: v for k, v in sorted(job_profile_data.items(), key=custom_sort)}
        else:
            def custom_sort_date(item):
                if "created_at" in item[1]:    
                    # 2020-06-17 15:12:44.156000
                    return datetime.strptime(item[1]["created_at"], '%Y-%m-%d %H:%M:%S.%f')
                else:
                    return -1

            job_profile_data = {k: v for k, v in sorted(job_profile_data.items(), key=custom_sort_date)}



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

        logger.info("tag count map")
        logger.info(tag_count_map)
    
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
            logger.info("tag id %s", tags[0])
            ret =  r.get(tags[0] + "_filter")
            if ret is not None:
                print("here loaded")
                ret = json.loads(ret)
            else:
                ret = {}
        else:
            ret = {}
            
        if len(filter) > 0:
            for key in ret:
                print(key)
                if key not in filter:
                    continue 
                
                print("key found in filter" , key)
                for rangekey in ret[key]:
                    if rangekey not in filter[key]:
                        continue

                    logger.info("range key %s", rangekey)

                    range = ret[key][rangekey]
                    if "children" not in range:
                        range["children"]  = []

                    children = range["children"]
                    newChildren = []
                    for child in children:
                        if isinstance(child, dict):
                            child_id = list(child.keys())[0]
                        else:
                            child_id = child

                        logger.info(child_id)
                        if child_id in job_profile_data:
                            newChildren.append(child)
                            filter_tag_children[child_id] = job_profile_data[child_id]
                        else:
                            logger.info("doesnt exist")
                            pass
                    
                    # logger.info("new children %s", newChildren)
                    ret[key][rangekey]["tag_count"] = len(newChildren)
                    ret[key][rangekey]["children"] = newChildren
                    if "merge" in ret[key][rangekey]:
                        del ret[key][rangekey]["merge"]
            
            # logger.info("filter data %s", len(filter_tag_children))
            job_profile_data = filter_tag_children

        paged_candidate_map = {}
        for idx, child_id in  enumerate(job_profile_data):
            if idx >= page * limit and idx < limit * (page + 1):
                doc = job_profile_data[child_id]
                if len(filter) == 0:
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

                            if "newCompressedStructuredContent" in cvParsedInfo:
                                del cvParsedInfo["newCompressedStructuredContent"]
                            
                        else:
                            cvParsedInfo = {}

                        doc = {
                            "cvParsedInfo" : cvParsedInfo
                        }
                    
                paged_candidate_map[child_id] = doc


        
        
        
        
        logger.info("sending response..")
        
        response = json.dumps({
            "filter" : ret,
            "candidate_map" : paged_candidate_map,
            "candidate_len" : len(paged_candidate_map),
            "tag_count_map" : tag_count_map
        })
        if len(filter) == 0:
            r.set(unique_cache_key, response)
            unique_cache_key_list.append(unique_cache_key)

        return response
    else:
        paged_tag_map = {}
        def custom_tag_sort(item):
            if "sequence" not in item:
                return -1 

            # logger.info(float(item[1]["sequence"]))
            return float(item["sequence"])  * -1

        logger.info("generating response..")
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

                


        logger.info("response completed..")
        response =  json.dumps(paged_tag_map)

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
            response =  json.dumps(response)

        if len(filter) == 0:
            r.set(unique_cache_key, response)
            unique_cache_key_list.append(unique_cache_key)

        return response
            

def clear_unique_cache(job_profile_id, tag_id, account_name = "", account_config = {}):
    r = connect_redis(account_name, account_config)
    print("clearning unique cache for ", job_profile_id, " XXXXX ", tag_id)
    global unique_cache_key_list
    new_unique_cache_key_list = []
    for rkey in unique_cache_key_list:
        # basically delete the unique_cache_key below if job data changes
        if job_profile_id in rkey:
            logger.info("cleaching cache %s", rkey)
            r.delete(rkey)
        else:
            new_unique_cache_key_list.append(rkey)
    
    unique_cache_key_list = new_unique_cache_key_list
    return unique_cache_key_list


def index(mongoid, filter_type="job_profile", account_name = "", account_config = {}):
    data = [] 
    global unique_cache_key_list

    logger.info("index called %s", mongoid)
    r = connect_redis(account_name, account_config)

    if filter_type == "full_data":
        data = r.get("full_data")
        if data:
            dataMap = json.loads(data)
            data = []
            for dkey in dataMap:
                data.append(dataMap[dkey])
        else:
            data = []

        key = "full_data"
        logger.info("data len %s" , len(data))
        generateFilterMap(key, data, account_name, account_config)
        logger.info("idex completed full data")
        return {}
            
    elif filter_type == "job_profile":
        data = r.get("job_" + mongoid)

        new_unique_cache_key_list = []
        for rkey in unique_cache_key_list:
            # basically delete the unique_cache_key below if job data changes
            if "on_ai_data" in rkey and mongoid in rkey:
                logger.info("cleaching cache %s", rkey)
                r.delete(rkey)
            else:
                new_unique_cache_key_list.append(rkey)

        unique_cache_key_list = new_unique_cache_key_list
        
            # if "on_ai_data" in rkey and mongoid in rkey and "_func" not in key:
            #     logger.info("cleaching cache %s", rkey)
            #     r.delete(rkey)

            #     func_data = r.get(rkey + "_func")
            #     obj = json.loads(func_data)
            #     mongoid = obj["mongoid"]
            #     filter_type = obj["filter_type"]
            #     tags = obj["tags"]
            #     page = obj["page"]
            #     limit = obj["limit"]
            #     on_ai_data = obj["on_ai_data"]
            #     filter = obj["filter"]
            #     account_name = obj["account_name"]
            #     account_config = obj["account_config"]

            #     r.delete(rkey + "_func")
 
        if data:            
            dataMap = json.loads(data)
        else:
            dataMap = []

        data = []
        tag_data_map = {}
        for dkey in dataMap:
            data.append(dataMap[dkey])
            if dataMap[dkey]["tag_id"] not in tag_data_map:
                tag_data_map[dataMap[dkey]["tag_id"]] = []
            
            tag_data_map[dataMap[dkey]["tag_id"]].append(dataMap[dkey])

        key = mongoid

        for tag_id in tag_data_map:
            logger.info("data len %s for key %s" , len(tag_data_map[tag_id]), tag_id)
            generateFilterMap(tag_id, tag_data_map[tag_id], account_name, account_config)
    

        logger.info("idex completed job profile data")
        return {}



        

    elif filter_type == "candidate":
        data = r.get("classify_" + mongoid)

        new_unique_cache_key_list = []
        for rkey in unique_cache_key_list:
            # basically delete the unique_cache_key below if job data changes
            if "on_ai_data" in rkey and mongoid in rkey:
                logger.info("cleaching cache %s", rkey)
                r.delete(rkey)
            else:
                new_unique_cache_key_list.append(rkey)

        unique_cache_key_list = new_unique_cache_key_list 
        

        if data:
            dataMap = json.loads(data)
        else:
            dataMap = []

        
        

        data = []
        for dkey in dataMap:
            data.append(dataMap[dkey])

        key = mongoid

        r.set("classify_" + mongoid + "_len", len(data))
        logger.info("adding to key %s", "classify_" + mongoid + "_len")

        

        logger.info("data len %s" , len(data))
        generateFilterMap(key, data, account_name, account_config)
        logger.info("idex completed candidate data")
        return {}

    
def generateFilterMap(key, data, account_name, account_config):


    logger.info("generating filter .......................")
    r = connect_redis(account_name, account_config)
    key = str(key)
    wrkExpList = []
    gpeList = []

    wrkExpIdxMap = {}
    gpeIdxMap = {}
    exp_map = {}
    education_map = {}
    for row in data:


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

    exp_filter = getExperianceRange(exp_map)
    edu_filter = getEducationFilters(education_map)
    work_filter = designation(wrkExpList, wrkExpIdxMap)
    gpe_filter = location(gpeList,gpeIdxMap)

    r.set(key + "_filter" , json.dumps({
        "exp_filter" : exp_filter,
        "edu_filter" : edu_filter,
        "work_filter" : work_filter,
        "gpe_filter" : gpe_filter
    }))

    logger.info("completed for key %s", key)

    return {"key" : key}