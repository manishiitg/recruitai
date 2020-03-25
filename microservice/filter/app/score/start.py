from app.logging import logger
from app.filter.util import parse_experiance_years, getCourseDict, matchCourse, getCourseDict
import redis

import os
import json

from bson.objectid import ObjectId
from pymongo import MongoClient

def get_education_display(degree):
    course_dict = getCourseDict()
    if degree is None or len(degree) == 0:
        return list(course_dict.keys())
    else:
        if degree in course_dict:
            courses = course_dict[degree]
            ret = []
            for course in courses:
                ret.append(course.split(":")[-1])
            
            return ret
        else:
            return {}


def getSampleCriteria():
    criteria = {
        "experiance" : {
            "min" : 6 * 31,
            "max" :12 * 31,
            "weight" : 5
        },
        "gender" : {
            "value": "male",
            "weight" : 5
        },
        "skills" : {
            "weight" : 5,
            "values" : {
                'php' : 9,
                "mysql" : 5,
                "css" : 2,
                "upwork" : 10
            }

        },
        "degree" : {
            "weight" : 5,
            "value" : "diploma"
        },
        "course" : {
            "weight" : 5,
            "values" : {
                "b.tech" : 9,
                "mca" : 8,
                "bca" : 5
            }
        }

    }
    return criteria


r = redis.Redis(host=os.environ.get("REDIS_HOST","redis"), port=os.environ.get("REDIS_PORT",6379), db=0)

db = None
def initDB():
    global db
    if db is None:
        client = MongoClient(os.getenv("RECRUIT_BACKEND_DB")) 
        db = client[os.getenv("RECRUIT_BACKEND_DATABASE")]

    return db


def get_candidate_score(id, criteria = None):
    max_score = 10

    if criteria is None:
        criteria = getSampleCriteria()

    candidate_score = 0
    db = initDB()
    # row = r.get(id)
    # if row:
    #     row = json.loads(row)
    # else:
    #     row = {}

    row = db.emailStored.find_one({
        'cvParsedInfo': {"$exists": True},
        "_id" : ObjectId(id)
    })
    
    total_weight = 0
    for cri in criteria:
        weight = criteria[cri]["weight"]
        total_weight += weight

    for cri in criteria:
        weight = criteria[cri]["weight"]
        logger.info( "criterial %s weight %s" , cri,  weight/total_weight  * max_score)

    candidate_score += getExpScore(criteria, row, total_weight, max_score)
    candidate_score += getGenderScore(criteria, row, total_weight, max_score)
    candidate_score += getSkillScore(criteria, row, total_weight, max_score)
    candidate_score += getEducationScore(criteria, row, total_weight, max_score)

    logger.info("final candidate score %s", candidate_score)

    db.emailStored.update_one({
        "_id" : ObjectId(id)
    }, {
        "$set" : {
            "cvParsedInfo.candidate_score" : candidate_score
        }
    })

    return candidate_score



def getExpScore(criteria, row, total_weight, max_score):
    candidate_score = 0
    if criteria["experiance"]["weight"] > 0:
        if "cvParsedInfo" in row and "finalEntity" in row["cvParsedInfo"]:    
            if "ExperianceYears" in row["cvParsedInfo"]["finalEntity"]:
                ExperianceYears = row["cvParsedInfo"]["finalEntity"]["ExperianceYears"]
                days, _, _ =  parse_experiance_years(ExperianceYears["obj"])
                                
                exp = criteria["experiance"]
                if days >= exp["min"] and days < exp["max"]:
                    candidate_score += exp["weight"]/total_weight  * max_score
                    logger.info("exp matched candidate score %s", candidate_score)
                else:
                    logger.info("exp not matched")

    return candidate_score


def getGenderScore(criteria, row, total_weight, max_score):
    candidate_score = 0
    if criteria["gender"]["weight"] > 0:
        gender = ""
        if "cvData" in row:
            if len(row["cvData"]) > 0:
                if "data" in row["cvData"][0]:
                    gender = row["cvData"][0]["data"]["gender"].lower()

        if len(gender) == 0:
            if "cvParsedInfo" in row and "finalEntity" in row["cvParsedInfo"]:    
                if "gender" in row["cvParsedInfo"]["finalEntity"]:
                    gender = row["cvParsedInfo"]["finalEntity"]["gender"][0].lower()

        if gender == criteria["gender"]["value"].lower():
            candidate_score += criteria["gender"]["weight"]/total_weight  * max_score
            logger.info("gender matched candidate score %s", candidate_score)
        else:
            logger.info("gender not matched %s", gender)

    return candidate_score

def getEducationScore(criteria, row, total_weight, max_score):
    candidate_score = 0
    courses_dict = getCourseDict()
    if criteria["degree"]["weight"] > 0 or criteria["course"]["weight"] > 0:
        EducationDegree = []
        if "cvParsedInfo" in row and "finalEntity" in row["cvParsedInfo"]:    
            EducationDegree = []
            if "EducationDegree" in row["cvParsedInfo"]["finalEntity"]:
                EducationDegree.append(row["cvParsedInfo"]["finalEntity"]["EducationDegree"]["obj"])
            
            if "education"  in row["cvParsedInfo"]["finalEntity"]:
                education = row["cvParsedInfo"]["finalEntity"]["education"]
                for edu in education:
                    for e in edu:
                        if "EducationDegree" in e:
                            EducationDegree.append(e["EducationDegree"])

        for edu in EducationDegree:
            final_course = matchCourse(edu)
            logger.info(final_course)
            if len(final_course) > 0:
                final_course = final_course[0]

            if criteria["degree"]["weight"] > 0:
                if "level" in final_course:
                    level = final_course["level"]
                    degree = criteria["degree"]["value"]

                    found = False
                    degreeMatch = False
                    for key in courses_dict:
                        if key == degree:
                            found = True

                        if found and key == level:
                            degreeMatch = True

                    if not found:
                        logger.info("major issue")

                    if degreeMatch:
                        candidate_score += criteria["degree"]["weight"]/total_weight  * max_score
                        logger.info("matched degeree candidate sore %s", candidate_score)
                    else:
                        logger.info("education degree not matching")

            if criteria["course"]["weight"] > 0:
                if "full" in final_course:
                    full = final_course["full"]
                    values = criteria["course"]["values"]
                    total_value_weight = 0
                    for value in values:
                        weight = values[value]
                        total_value_weight += weight

                    for value in values:
                        weight = values[value]
                        if value == full.split(":")[-1].lower():
                            candidate_score += criteria["course"]["weight"]/total_weight  * max_score * (weight/total_value_weight)
                            logger.info("course matched %s candidate score %s", value, candidate_score)

    return candidate_score

def getSkillScore(criteria, row, total_weight, max_score):
    candidate_score = 0

    if criteria["skills"]["weight"] > 0:
      values = criteria["skills"]["values"]
      total_value_weight = 0
      for value in values:
        weight = values[value]
        total_value_weight += weight

      skillCandidateScore = 0
      if "cvParsedInfo" in row:     
        if "skillExtracted" in row["cvParsedInfo"] and row["cvParsedInfo"]["skillExtracted"] is not None:
          skillExtracted = row["cvParsedInfo"]["skillExtracted"]
          score = skillExtracted[str(row["_id"])]["score"]
          skillCandidateScore = 0

          for value in values:
            weight = values[value]
            found = False
            for skill in score:
              if skill in value:
                found = True
                max_dist = 0    
                for key in score[skill]:  
                  dist = score[skill][key]
                  if dist < .75:
                    dist = 1 - dist

                    # print(dist , " ===== " , skill  , " ======  ", key)
                    if dist > max_dist:
                      max_dist = dist
                    
                
                break

            if found:
              skillCandidateScore += max_dist * weight / total_value_weight
              logger.info("skill score %s %s %s" , skillCandidateScore , max_dist, value)
            else:
              logger.info("strange skill not found %s", value)

      if skillCandidateScore > 0:
          candidate_score += skillCandidateScore *  criteria["skills"]["weight"]/total_weight * max_score
          logger.info("candidate score updated %s", candidate_score)

    return candidate_score