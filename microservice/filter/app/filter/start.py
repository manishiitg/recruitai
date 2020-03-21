from app.logging import logger
from pymongo import MongoClient

from app.filter.util import parse_experiance_years, matchCourse, designation, location, cleanLocation, cleanWorkExp

import redis

r = redis.Redis(host=os.environ.get("REDIS_HOST","redis"), port=os.environ.get("REDIS_PORT",6379), db=0)
db = None
def initDB():
    global db
    if db is None:
        client = MongoClient(os.environ.get("RECRUIT_BACKEND_DB" , "mongodb://176.9.137.77:27017/hr_recruit_dev"))
        db = client[os.environ.get("RECRUIT_BACKEND_DATABASe" , "hr_recruit_dev")]

    return db



def start(mongoid, filter_type="job_profile"):

    db = initDB()


    data = [] 

    if filter_type == "job_profile":
        data = r.get("job_" + mongoid)
        data = json.loads(data)
        

    elif filter_type == "candidate":
        data = r.get("classify_" + mongoid)
        data = json.loads(data)

    wrkExpList = []
    gpeList = []

    designation_map = {}
    location_map = {}
    for row in data:
        if "finalEntity" in row["cvParsedInfo"]:    
            if "ExperianceYears" in row["cvParsedInfo"]["finalEntity"]:
                ExperianceYears = row["cvParsedInfo"]["finalEntitey"]["ExperianceYears"]
                # print(ExperianceYears["obj"])

                days, _, _ =  parse_experiance_years(ExperianceYears["obj"])

            if "EducationDegree" in row["cvParsedInfo"]["finalEntity"]:
                EducationDegree = row["cvParsedInfo"]["finalEntity"]["EducationDegree"]
                education = matchCourse(EducationDegree["obj"])

            if "wrkExp" in row["cvParsedInfo"]["finalEntity"]:
                wrkExp = row["cvParsedInfo"]["finalEntity"]["wrkExp"]
                if wrkExp:
                    for w in wrkExp:
                        if "Designation" in w[0]:
                            wrkExpList.append(w[0]["Designation"])
                            designation_map[str(row["_id"])] = w[0]["Designation"]

            if "GPE" in row["cvParsedInfo"]["finalEntity"]:
                GPE = row["cvParsedInfo"]["finalEntity"]["GPE"]
                if GPE:
                    gpeList.append(GPE["obj"])
                    designation_map[str(row["_id"])] = GPE["obj"]

    wrkCombineList = designation(wrkExpList)
    gpeCombineList = location(gpeList)

    for key in designation_map:
        desg = designation_map[key]
        desg = cleanWorkExp(desg)
        found = False
        for key in wrkCombineList:

            if desg == key:
                found = True
                break

            data = wrkCombineList[key]
            count = data["count"]
            merge = data["merge"]

            for m in merge:
                if desg == m:
                    found = True
                    break

        if not found:
            logger.info("not found for %s", desg)

    




    pass