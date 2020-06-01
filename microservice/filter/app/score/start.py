from app.logging import logger
from app.filter.util import parse_experiance_years, getCourseDict, matchCourse, getCourseDict, get_exp_display_range
import redis

import os
import json

from bson.objectid import ObjectId
from pymongo import MongoClient


from app.account import initDB, connect_redis

def get_exp_display(account_name, account_config):
    return get_exp_display_range()


def get_education_display(degree, account_name, account_config):
    course_dict = getCourseDict()
    if degree is None or len(degree) == 0:
        return list(course_dict.keys())
    else:
        if degree == "full":
            return course_dict

        if degree in course_dict:
            courses = course_dict[degree]
            ret = []
            for course in courses:
                ret.append(course.split(":"))
            
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


def get_candidate_score(id, account_name, account_config, criteria = None):

    if not ObjectId.is_valid(id):
        return 0

    max_score = 10

    if criteria is None:
        criteria = getSampleCriteria()

    candidate_score = 0
    full_debug = []
    db = initDB(account_name, account_config)
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

    if row:
        
        exp_score, debug = getExpScore(criteria, row, total_weight, max_score)
        candidate_score += exp_score
        full_debug.extend(debug)

        gender_score, debug = getGenderScore(criteria, row, total_weight, max_score)
        
        candidate_score += gender_score
        full_debug.extend(debug)


        skill_score, debug = getSkillScore(criteria, row, total_weight, max_score)
        candidate_score += skill_score
        full_debug.extend(debug)

        edu_score, debug = getEducationScore(criteria, row, total_weight, max_score)
        candidate_score += edu_score
        full_debug.extend(debug)

    logger.info("final candidate score %s", candidate_score)

    db.emailStored.update_one({
        "_id" : ObjectId(id)
    }, {
        "$set" : {
            "cvParsedInfo.candidate_score" : candidate_score,
            "cvParsedInfo.candidate_score_debug" : full_debug
        }
    })

    return candidate_score



def getExpScore(criteria, row, total_weight, max_score):
    candidate_score = 0
    debug = []
    if criteria["experiance"]["weight"] > 0:
        debug.append("Work Exp Criteria %s" % json.dumps(criteria["experiance"], indent=True))
        if row and "cvParsedInfo" in row and "finalEntity" in row["cvParsedInfo"]:    
            if "ExperianceYears" in row["cvParsedInfo"]["finalEntity"]:
                ExperianceYears = row["cvParsedInfo"]["finalEntity"]["ExperianceYears"]
                days, _, _ =  parse_experiance_years(ExperianceYears["obj"])
                                
                exp = criteria["experiance"]
                if days >= exp["min"] and days < exp["max"]:
                    candidate_score += exp["weight"]/total_weight  * max_score
                    logger.info("exp matched candidate score %s", candidate_score)
                    debug.append("exp matched candidate score %s" % candidate_score)
                else:
                    logger.info("exp not matched")
    
    if candidate_score == 0:
        debug.append("exp not matched")

    return candidate_score, debug


def getGenderScore(criteria, row, total_weight, max_score):
    candidate_score = 0
    debug = []
    if criteria["gender"]["weight"] > 0:
        debug.append("Gender Score Criteria %s" % json.dumps(criteria["gender"], indent=True))
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
            debug.append("gender matched candidate score %s" % candidate_score)
        else:
            logger.info("gender not matched %s", gender)
            debug.append("gender not matched %s" % gender)

    return candidate_score, debug

def getEducationScore(criteria, row, total_weight, max_score):
    candidate_score = 0
    debug = []
    courses_dict = getCourseDict()
    if criteria["degree"]["weight"] > 0 or criteria["course"]["weight"] > 0:
        debug.append("Education Score Criteria %s" % json.dumps(criteria["degree"], indent=True))
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
                        debug.append("matched degeree candidate sore %s" % candidate_score)
                    else:
                        logger.info("education degree not matching")
                        debug.append("education degree not matching")

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
                            debug.append("course matched %s candidate score %s" % (value, candidate_score))

    return candidate_score, debug

def getSkillScore(criteria, row, total_weight, max_score):
    candidate_score = 0
    debug = []
    if criteria["skills"]["weight"] > 0:
      debug.append("skill Score Criteria %s"  %  json.dumps(criteria["skills"], indent=True))
      values = criteria["skills"]["values"]
      total_value_weight = 0
      for value in values:
        weight = values[value]
        total_value_weight += weight

      skillCandidateScore = 0
      if "cvParsedInfo" in row:     
        if "skillExtracted" in row["cvParsedInfo"] and row["cvParsedInfo"]["skillExtracted"] is not None:
          skillExtracted = row["cvParsedInfo"]["skillExtracted"]
          if str(row["_id"]) in skillExtracted:
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
                        debug.append("skill score %s %s %s" % (skillCandidateScore , max_dist, value))
                    else:
                        logger.info("strange skill not found %s", value)
                        debug.append("strange skill not found %s" % value)

      if skillCandidateScore > 0:
          candidate_score += skillCandidateScore *  criteria["skills"]["weight"]/total_weight * max_score
          logger.info("candidate score updated %s", candidate_score)
          debug.append("candidate score updated %s", candidate_score)
      else:
          debug.append("skill not matched")

    return candidate_score, debug