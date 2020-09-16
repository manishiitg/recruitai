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
        # 
        # "experiance": {
        #     "weight": 5,
        #     "values": [
        #         {
        #             "min": 0,
        #             "max": 372,
        #             "weight": 5
        #         }
        #     ]
        # },
        # "gender": {
        #     "value": "male",
        #     "weight": 5
        # },
        # "skills": {
        #     "weight": 5,
        #     "values": [
        #         {"value": "angular_js", "weight": 9},
        #         {"value": "mysql", "weight": 9},
        #         {"value": "css", "weight": 9},
        #         {"value": "upwork", "weight": 9}
        #     ]
        # },
        # "education": {
        #     "weight": 5,
        #     "values": [
        #         {
        #             "value": "Bachelor of Engineering:Bachelor of Technology:B.E:B.Tech",
        #             "weight": 10,
        #             "type": "course"
        #         },
        #         {
        #             "value": "masters",
        #             "weight": 10,
        #             "type": "degree"
        #         }
        #     ]
        # 

    }
    return criteria

def get_candidate_score_bulk(id, account_name, account_config, criteria):
    data = getSampleData(id, account_name, account_config)
    ret_data = {}
    for row in data:
        ret = get_candidate_score(row["_id"], account_name, account_config, criteria, row, True)
        ret_data[row["_id"]] = ret

    return ret_data
    


def getSampleData(mongoid, account_name, account_config):
    db = initDB(account_name, account_config)    
    r = connect_redis(account_name, account_config)

    logger.info("getting sample for %s", mongoid)
    data = None
    if "all" in mongoid:
        mongoid = mongoid.replace("all:", "")
        if ":" in mongoid:
            skip = int(mongoid[mongoid.index(":")+1:])
            mongoid = mongoid[:mongoid.index(":")]
        else:
            skip = 0

        
        if r.exists("job_" + mongoid):
            logger.info("data from redis")
            data = r.get("job_" + mongoid)
            # logger.info("data from redis %s", data)
            dataMap = json.loads(data)
            data = []
            for key in dataMap:
                data.append(dataMap[key])
                
            logger.info("candidate full data found %s", len(data))
        else:
            

            logger.info("final mongo id %s", mongoid)
            logger.info("skip %s", skip)
            ret = db.emailStored.find({ "job_profile_id": mongoid, "cvParsedInfo.debug" : {"$exists" : True} } , {"cvParsedInfo":1, "_id" : 1})
            jobMap = []
            
            for row in ret:
                row["_id"] = str(row["_id"])
                r.set(row["_id"], json.dumps(row, default=str))
                jobMap.append(row)

            data = jobMap
            r.set("job_" + mongoid  , json.dumps(jobMap))

    elif "," in mongoid:
        mongoid = mongoid.split(",")

        data = []
        for mid in mongoid:
            if r.exists(mid):
                logger.info("data from redis")
                row = r.get(mid)
                data.append(json.loads(row))
            else:
                logger.info("data from mongo")
                row = db.emailStored.find_one({ 
                    "_id" : ObjectId(mid)
                })
                row["_id"] = str(row["_id"])
                r.set(mid, json.dumps(row, default=str))
                data.append(row)

            
    else:
        if r.exists(mongoid):
            logger.info("data from redis")
            row = json.loads(r.get(mongoid))
            data = [row]
        else:
            logger.info("data from mongo")
            row = db.emailStored.find_one({ 
                "_id" : ObjectId(mongoid)
            })
            if row:
                row["_id"] = str(row["_id"])
                data = [row]
                r.set(mongoid, json.dumps(row, default=str))

    logger.info("processing data line %s", len(data))

    return data

def get_candidate_score(id, account_name, account_config, criteria = None, candidate_row = None, updated_db = True):

    if not ObjectId.is_valid(id):
        return -1

    max_score = 10

    if criteria is None:
        # criteria = getSampleCriteria()
        return -1

    candidate_score = 0
    full_debug = []
    db = initDB(account_name, account_config)
    # row = r.get(id)
    # if row:
    #     row = json.loads(row)
    # else:
    #     row = {}

    if not candidate_row:
        row = db.emailStored.find_one({
            'cvParsedInfo': {"$exists": True},
            "_id" : ObjectId(id)
        })
    else:
        row = candidate_row

    
    total_weight = 0
    for cri in criteria:
        if type(criteria[cri]) is dict and "weight" in criteria[cri]:
            weight = int(criteria[cri]["weight"])
            total_weight += weight

    for cri in criteria:
        if type(criteria[cri]) is dict and "weight" in criteria[cri]:
            weight = criteria[cri]["weight"]
            debug_str = "criteria {} weight {}".format(cri,  weight/total_weight  * max_score)
            logger.info(debug_str)
            full_debug.append(debug_str)

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

    if updated_db:
        db.emailStored.update_one({
            "_id" : ObjectId(id)
        }, {
            "$set" : {
                "cvParsedInfo.candidate_score" : candidate_score,
                "cvParsedInfo.candidate_score_debug" : full_debug
            }
        })

    return {
        "candidate_score" : candidate_score,
        "candidate_score_debug" : full_debug
    }



def getExpScore(criteria, row, total_weight, max_score):
    candidate_score = 0
    debug = []
    
    if "experiance" not in criteria:
        logger.info("experiance not found")
        debug.append("experiance not found")
        return candidate_score, debug

    if "weight" not in criteria["experiance"]:
        criteria["experiance"]['weight'] = 0

    if criteria["experiance"]["weight"] > 0:
        logger.info("Work experiance critera %s", json.dumps(criteria["experiance"], indent=True))
        debug.append("Work Experiance Criteria %s" % json.dumps(criteria["experiance"], indent=True))
        if row and "cvParsedInfo" in row and "finalEntity" in row["cvParsedInfo"]:    
            if "ExperianceYears" in row["cvParsedInfo"]["finalEntity"]:
                ExperianceYears = row["cvParsedInfo"]["finalEntity"]["ExperianceYears"]
                days, _, _ =  parse_experiance_years(ExperianceYears["obj"])
                                
                debug_str = "candidate experiance year {} and parsed experiance {}".format(ExperianceYears, days)
                logger.info(debug_str)
                debug.append(debug_str)

                # exp = criteria["experiance"]
                total_exp_weight = 0
                for exp in criteria["experiance"]["values"]:
                    if "weight" in exp:
                        total_exp_weight += exp["weight"]

                debug_str = "experiance weight {}".format(total_exp_weight)
                logger.info(debug_str)
                debug.append(debug_str)

                if total_exp_weight > 0:
                    for exp in criteria["experiance"]["values"]:
                        weight = exp["weight"]
                        if days >= exp["min"] and days < exp["max"]:
                            debug_str = "exp criteria match min days {} max days {} weight {}".format(exp["min"], exp["max"], exp["weight"]) 
                            logger.info(debug_str)
                            debug.append(debug_str)

                            exp_score = (exp["weight"] / total_exp_weight)  * max_score /total_weight
                            candidate_score += exp_score

                            debug_str = "exp matched score {}".format(exp_score)
                            logger.info(debug_str)
                            debug.append(debug_str)

                            debug_str = "exp matched total candidate score {}".format(candidate_score)
                            logger.info(debug_str)
                            debug.append(debug_str)

                        else:
                            debug_str = "exp not matched for min exp {} max exp {}".format(exp["min"], exp["max"]) 
                            logger.info(debug_str)
                            debug.append(debug_str)
            else:
                debug_str = "candidate does not have any experiance" 
                logger.info(debug_str)
                debug.append(debug_str)        
        else:
            debug_str = "not ai data found" 
            logger.info(debug_str)
            debug.append(debug_str)      

    else:
        debug_str = "experiance criteria not weight is 0" 
        logger.info(debug_str)
        debug.append(debug_str)

    return candidate_score, debug


def getGenderScore(criteria, row, total_weight, max_score):
    candidate_score = 0
    debug = []
    if "gender" not in criteria:
        debug_str = "gender not found"
        logger.info(debug_str)
        debug.append(debug_str)
        return candidate_score, debug

    if "weight" not in criteria["gender"]:
        criteria["gender"]["weight"] = 0
        
    if criteria["gender"]["weight"] > 0:
        debug_str = "Gender Score Criteria {}".format(json.dumps(criteria["gender"], indent=True))
        logger.info(debug_str)
        debug.append(debug_str)
        gender = ""
        if "cvData" in row and row["cvData"]:
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

    if "education" not in criteria:
        return candidate_score, debug

    if "weight" not in criteria["education"]:
        criteria["education"]['weight'] = 0

    if criteria["education"]["weight"] > 0:
        debug_str = "Education Score Criteria {}".format(json.dumps(criteria["education"], indent=True))
        logger.info(debug_str)
        debug.append(debug_str)
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
            debug_str = "final course found {} for ner {} ".format(final_course, edu)
            logger.info(debug_str)
            debug.append(debug_str)

            if len(final_course) > 0:
                final_course = final_course[0]

            total_degree_weight = 0
            total_course_weight = 0
            for edu_criteria in criteria["education"]["values"]:
                if edu_criteria["type"] == "degree":
                    total_degree_weight += edu_criteria["weight"]

                if edu_criteria["type"] == "course":
                    total_course_weight += edu_criteria["weight"]

            for edu_criteria in criteria["education"]["values"]:
                if edu_criteria["type"] == "degree":
                    if "level" in final_course:
                        level = final_course["level"]
                        degree = edu_criteria["value"]

                        found = False
                        degreeMatch = False
                        for key in courses_dict:
                            if key == degree:
                                found = True

                            if found and key == level:
                                degreeMatch = True

                        if not found:
                            logger.info("degree not found issue dgree: {} level: {}".format(degree, level))
                            

                        if degreeMatch:
                            candidate_score += (edu_criteria["weight"] / (total_degree_weight + total_course_weight) )/total_weight  * max_score
                            logger.info("matched degeree candidate sore %s", candidate_score)
                            debug.append("matched degeree candidate sore %s" % candidate_score)
                        else:
                            logger.info("education degree not matching")
                            debug.append("education degree not matching")

            for edu_criteria in criteria["education"]["values"]:
                if edu_criteria["type"] == "course":
                    if "full" in final_course:
                        full = final_course["full"]
                        # values = criteria["course"]["values"]
                        # total_value_weight = 0
                        # for value in values:
                        #     weight = values[value]
                        #     total_value_weight += weight

                        
                        # if edu_criteria["value"] == full.split(":")[-1].lower():
                        if edu_criteria["value"] == full:
                            candidate_score += edu_criteria["weight"]/(total_degree_weight + total_course_weight) /total_weight  * max_score
                            logger.info("course matched %s candidate score %s", edu_criteria["value"], candidate_score)
                            debug.append("course matched %s candidate score %s" % (edu_criteria["value"], candidate_score))

    return candidate_score, debug

def getSkillScore(criteria, row, total_weight, max_score):
    candidate_score = 0
    debug = []
    if "skills" not in criteria:
        return candidate_score, debug
    
    if "weight" not in criteria["skills"]:
        criteria["skills"]['weight'] = 0

    if criteria["skills"]["weight"] > 0:
      logger.info("skill Score Criteria %s"  %  json.dumps(criteria["skills"], indent=True))
      debug.append("skill Score Criteria %s"  %  json.dumps(criteria["skills"], indent=True))
      values = criteria["skills"]["values"]
      total_value_weight = 0
      for obj in values:
        if "weight" in obj:
            total_value_weight += obj["weight"]

      skillCandidateScore = 0
      if "cvParsedInfo" in row and total_value_weight > 0:     
        if "skillExtracted" in row["cvParsedInfo"] and row["cvParsedInfo"]["skillExtracted"] is not None:
          skillExtracted = row["cvParsedInfo"]["skillExtracted"]
          print(skillExtracted)
          print(row["_id"])
          if str(row["_id"]) in skillExtracted:
            
            if "score" in skillExtracted[str(row["_id"])]:
                score = skillExtracted[str(row["_id"])]["score"]
                skillCandidateScore = 0
                print("skill scoreeeeeeee") 
                print(score)

                for obj in criteria["skills"]["values"]:
                    weight = obj["weight"]
                    skill_value = obj["value"]
                    found = False
                    for skill in score:
                        logger.info("skill matching {} == {}".format(skill_value, skill))
                        if skill == skill_value or skill_value.replace("_","") == skill.replace("_","") or skill_value.replace(" ","") == skill.replace(" ",""):
                            found = True
                            max_dist = 0   
                            
                            for key in score[skill]:  
                                dist = score[skill][key]
                                print(dist)
                                if dist < .75:
                                    dist = 1 - dist

                                    # print(dist , " ===== " , skill  , " ======  ", key)
                                    if dist > max_dist:
                                        max_dist = dist
                                    
                                
                                break

                        if found:
                            skillCandidateScore += max_dist * weight / total_value_weight
                            debug_str = "skill score skillCandidateScore {} max_dist {} value {}".format(skillCandidateScore , max_dist, skill_value)
                            logger.info(debug_str)
                            debug.append(debug_str)
                        else:
                            debug_str = "strange skill not found {}".format(skill_value)
                            logger.info(debug_str)
                            debug.append(debug_str)

      if skillCandidateScore > 0:
          candidate_score += skillCandidateScore *  criteria["skills"]["weight"]/total_weight * max_score
          debug_str = "candidate score updated {}".format(candidate_score)
          logger.info(debug_str)
          debug.append(debug_str)
      else:
          debug.append("skill not matched")
          logger.info("skill not matched")

    return candidate_score, debug