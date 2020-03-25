from app.logging import logger
from pymongo import MongoClient

from app.filter.util import parse_experiance_years, matchCourse, designation, location, getExperianceRange, getEducationFilters

import os
import redis
import json

from app.filter.util import getCourseDict

r = redis.Redis(host=os.environ.get("REDIS_HOST","redis"), port=os.environ.get("REDIS_PORT",6379), db=0)

def indexAll():
    data = r.get("full_data")
    if data:
        dataMap = json.loads(data)
        data = []
        for dkey in dataMap:
            data.append(dataMap[dkey])
        generateFilterMap("full_data",data)

    for key in r.scan_iter():
        key = key.decode("utf-8")
        if "_filter" in str(key):
            continue

        if "classify_" in str(key):
            data = r.get(key)
            dataMap = json.loads(data)
            data = []
            for dkey in dataMap:
                data.append(dataMap[dkey])
            key = str(key)
            generateFilterMap(key.replace("classify_",""),data)

        if "job_" in str(key):
            data = r.get(key)
            dataMap = json.loads(data)
            data = []
            for dkey in dataMap:
                data.append(dataMap[dkey])
            key = str(key)
            generateFilterMap(key.replace("job_",""),data)


def fetch(mongoid, filter_type="job_profile"):
    if filter_type == "full_data":
        return r.get("full_data_filter")

    ret =  r.get(mongoid + "_filter")
    if ret is None:
        return ""
    else:
        return ret

def index(mongoid, filter_type="job_profile"):
    data = [] 
    if filter_type == "full_data":
        data = r.get("full_data")
        if data:
            dataMap = json.loads(data)
            data = []
            for dkey in dataMap:
                data.append(dataMap[dkey])

            key = "full_data"
            
    if filter_type == "job_profile":
        data = r.get("job_" + mongoid)
        if data:            
            dataMap = json.loads(data)
        else:
            dataMap = []

        data = []
        for dkey in dataMap:
            data.append(dataMap[dkey])
        key = mongoid
        

    elif filter_type == "candidate":
        data = r.get("classify_" + mongoid)
        if data:
            dataMap = json.loads(data)
        else:
            dataMap = []

        data = []
        for dkey in dataMap:
            data.append(dataMap[dkey])
        key = mongoid

    return generateFilterMap(key, data)

    
def generateFilterMap(key, data):
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

            if "EducationDegree" in row["cvParsedInfo"]["finalEntity"]:
                EducationDegree = []
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