from app.logging import logger
from pymongo import MongoClient
import json
import random 

from scipy.spatial.distance import cosine

import numpy
from bson import json_util

import re
import os

from app.util import generate_ngrams

from app.skillsword2vec.start import loadModel, getDomainModel

import spacy
nlp = spacy.load('en')

from bson.objectid import ObjectId

import redis



import nmslib 
import time

# Set index parameters
# These are the most important onese
M = 50
efC = 2000

num_threads = 6 # server has 6 threads in processor

# Space name should correspond to the space name 
space_name='cosinesimil'

# Setting query-time parameters
efS = 100

def start(findSkills, mongoid, isGeneric = False, account_name = "", account_config = {}):
    docLines, total_documents, doc2Idx, domain = getSampleData(mongoid, account_name, account_config)

    if total_documents == 0:
        logger.critical("not docs found")
        return ""

    logger.critical("skills %s", findSkills)

    # extra new code. i will expand skills mainly to compensate for space and _

    newFindSkills = []
    for skill in findSkills:
        newFindSkills.append(skill)
        
        if "_" in skill:
            newFindSkills.append(skill.replace("_",""))
        if " " in skill:
            newFindSkills.append(skill.replace(" ",""))
    findSkills = newFindSkills

    logger.critical("domain %s", domain)
    model = getDomainModel(domain)
    data_matrix, word2Vec, word2Idx, word2Line, word2Doc = getWordMatrix(docLines, model)

    
    index_time_params = {'M': M, 'indexThreadQty': num_threads, 'efConstruction': efC, 'post' : 2}
    # logger.critical('Index-time parameters %s', index_time_params)


    # Intitialize the library, specify the space, the type of the vector and add data points 
    index = nmslib.init(method='hnsw', space=space_name, data_type=nmslib.DataType.DENSE_VECTOR) 
    index.addDataPointBatch(data_matrix)

    start = time.time()
    index_time_params = {'M': M, 'indexThreadQty': num_threads, 'efConstruction': efC}
    index.createIndex(index_time_params) 
    end = time.time() 
    # logger.critical('Index-time parameters %s', index_time_params)
    # logger.critical('Indexing time = %f' % (end-start))

    # index.saveIndex('dense_index_optim.bin')

    # newIndex = nmslib.init(method='hnsw', space=space_name, data_type=nmslib.DataType.DENSE_VECTOR) 
    # newIndex.loadIndex('dense_index_optim.bin')

    
    query_time_params = {'efSearch': efS}
    # logger.critical('Setting query-time parameters %s', query_time_params)
    index.setQueryTimeParams(query_time_params)


    #generate query matrix


    query_matrix, skillVec, querySkill, notFound = queryMatrix(model, findSkills)

    query_qty = query_matrix.shape[0]
    logger.critical("query qty: %s", query_qty)

    avg_dist = 0
    avg_count = 0
    max_dist = 0
    closest_dist = 0
    max_closest_dist  = 0

    # logger.critical(skillVec)

    if len(skillVec) == 0:
        return "empty skills"

    for idx, key in enumerate(querySkill):
        vec = querySkill[key]
        top1 = model.wv.most_similar(positive=[key] , topn=1)
        closest_dist += top1[0][1]
        if top1[0][1] > max_closest_dist:
            max_closest_dist = top1[0][1]

        for idx2, key2 in enumerate(querySkill):
            vec2 = querySkill[key2]
            if idx2 <= idx:
                continue

            dist = cosine(vec.reshape(-1,1), vec2.reshape(-1,1))
            avg_dist += dist
            avg_count += 1
            if dist > max_dist:
                max_dist = dist


    avg_closest_dist = closest_dist/len(findSkills)
    if avg_count != 0:
        logger.critical("avg distance between query words %s", avg_dist/avg_count)
    logger.info("max distance %s", max_dist)
    logger.info("avg closest distance %s", avg_closest_dist)
    logger.info("max closest distance %s", max_closest_dist)
    
    start = time.time() 
    # assume 20 skills per doc which is already a lot 
    # avergae is 5 or 6
    nbrs = index.knnQueryBatch(query_matrix, k = 20 * total_documents, num_threads = num_threads)
    end = time.time() 
    # print('kNN time total=%f (sec), per query=%f (sec), per query adjusted for thread number=%f (sec)' % 
    #     (end-start, float(end-start)/query_qty, num_threads*float(end-start)/query_qty))




    documents = {}

    wordIdx2Dist = {}


    distThresh = avg_closest_dist
    maxDistSkillThresh = max_closest_dist
    if avg_closest_dist > .7:
        avg_closest_dist = .7

    if maxDistSkillThresh > .9:
        maxDistSkillThresh = .9

    maxSkillDistCount = {}

    logger.info(" ===================================final algo ===================================")

    for idx, skill in enumerate(querySkill):
        logger.info("skill : %s",skill)
        logger.info("wordidx %s",  [word2Idx[w] for w in nbrs[idx][0]])
        logger.info("distances %s", nbrs[idx][1])
        # words = [] 
        wordIdx2Dist[skill] = {}
        for matchIdx, distance in  enumerate(nbrs[idx][1]):
            wordIdx = nbrs[idx][0][matchIdx]
            wordIdx2Dist[skill][wordIdx] = distance

            logger.info("distance %s", distance)
            orgLineIdx  = word2Line[wordIdx]
            orgDocIdx = word2Doc[wordIdx]

            if orgDocIdx not in documents:
                documents[orgDocIdx] = {}
    
            if orgLineIdx not in documents[orgDocIdx]:
                documents[orgDocIdx][orgLineIdx] = {}
            
            if skill not in documents[orgDocIdx][orgLineIdx]:
                documents[orgDocIdx][orgLineIdx][skill] = []

            if distance < distThresh:
                # words.append(word2Idx[wordIdx])
                logger.info("skill: %s dist: %s word: %s", skill, distance, word2Idx[wordIdx])
                documents[orgDocIdx][orgLineIdx][skill].append(wordIdx)
            else:
                logger.info("skill skipped: %s dist: %s word: %s", skill, distance, word2Idx[wordIdx])                

            if distance <= maxDistSkillThresh:
                
                logger.info("max skill: %s dist: %s word: %s", skill, maxDistSkillThresh, word2Idx[wordIdx])

                if orgDocIdx not in maxSkillDistCount:
                    maxSkillDistCount[orgDocIdx] = {}

                if orgLineIdx not in maxSkillDistCount[orgDocIdx]:
                    maxSkillDistCount[orgDocIdx][orgLineIdx] = {}
                
                if skill not in maxSkillDistCount[orgDocIdx][orgLineIdx]:
                    maxSkillDistCount[orgDocIdx][orgLineIdx][skill] = []

                maxSkillDistCount[orgDocIdx][orgLineIdx][skill].append( (wordIdx, distance) )


    logger.info(documents)
    logger.info("maxskilldist count")
    logger.info(maxSkillDistCount)

    finalSkillList = {}

    ### in this logical we are calculation just the global dist and count for query
    ### this is only using documents which is based on avg count

    for docIdx in range(total_documents):
        finalSkillList[doc2Idx[docIdx]] = {}
        globalSkillDist = {}
        if docIdx in documents:
            lines = documents[docIdx]
            for orgLineIdx in lines:
                for skill in lines[orgLineIdx]:
                    maxSkillCount = 3
                    for wordIdx in lines[orgLineIdx][skill]:

                        dist = wordIdx2Dist[skill][wordIdx]
                        logger.info("word: %s dist: %s skill: %s line: %s", word2Idx[wordIdx] ,dist ,  skill , orgLineIdx )
                        
                        if dist < .05 and not isGeneric:
                            maxSkillCount = 0

                        logger.info(lines[orgLineIdx][skill])
                        count = len(lines[orgLineIdx][skill])
                        if  count > maxSkillCount or count > len(querySkill) * .5:
                            logger.info("skill %s count %s maxcount count %s" ,skill, count, maxSkillCount)
                            logger.info("line index %s", orgLineIdx)
                            for idx in lines[orgLineIdx][skill]:
                                if word2Idx[idx] not in globalSkillDist:
                                    globalSkillDist[word2Idx[idx]] = {
                                        "dist" : wordIdx2Dist[skill][idx],
                                        "count" : 1
                                    }
                                else:
                                    globalSkillDist[word2Idx[idx]]["dist"] += wordIdx2Dist[skill][idx]
                                    globalSkillDist[word2Idx[idx]]["count"] += 1
                        else:
                            logger.info("count failed count %s actual count %s len(querySkill) %s",count, maxSkillCount, len(querySkill))

                        # print(word2Idx[idx])
        logger.info("global skill dist %s after docidx %s", globalSkillDist, docIdx)

        ### 
        ## this logic is based on max dist. in this we are seeing which keywords have come in max dist
        ## nad if these keywords count is more than qty * .5 then we add it skills
        if docIdx in maxSkillDistCount:
            lines = maxSkillDistCount[docIdx]
            for orgLineIdx in lines:
                idxCountMap = {}
                for skill in lines[orgLineIdx]:
                    matches = lines[orgLineIdx][skill]
                    for m in matches:
                        idx, dist = m
                        # print(word2Idx[idx], "====" , dist)
                        if word2Idx[idx] not in idxCountMap:
                            idxCountMap[word2Idx[idx]] = {
                                "count" : 0,
                                "dist" : 0
                            }

                        idxCountMap[word2Idx[idx]] = {
                            "count" : idxCountMap[word2Idx[idx]]["count"] + 1,
                            "dist" : idxCountMap[word2Idx[idx]]["dist"] + dist
                        }

                idxCountMap = {k: v for k, v in sorted(idxCountMap.items(), key=lambda item: item[1]["count"]  )}
                if len(idxCountMap) <= 1:
                    continue
                # print("idx count map")
                # print(idxCountMap)
                # print(query_qty * .5)
                for word in idxCountMap:
                    count = idxCountMap[word]["count"]
                    dist = idxCountMap[word]["dist"]
                    dist = dist/count
                    if count >= query_qty * .5 and count > 1:
                        if word not in globalSkillDist:
                            globalSkillDist[word] = {
                                "dist" : dist,
                                "count" : 1
                            }
                        else:
                            globalSkillDist[word]["dist"] += dist
                            globalSkillDist[word]["count"] += 1


                        logger.info("%s via broad skill match", word)
                    else:
                        pass
        else:
            logger.info("dockdix not in max skill dist %s", docIdx)
            
        logger.info("global skill maxdist %s after docidx %s", globalSkillDist, docIdx)

        if len(globalSkillDist) > 0:
            logger.info("final skills found for document %s", docIdx)
            sortDist = {}
            for word in globalSkillDist:
                if len(word.strip()) == 1:
                    #skip single letter mostly symbols
                    continue
                avgDist = globalSkillDist[word]["dist"] / globalSkillDist[word]["count"]
                # print(word , "====", avgDist)
                sortDist[word] = avgDist


            # sortDist = {k: v for k, v in sorted(sortDist.items(), key=lambda item: item) }
            # logger.critical(sortDist) # not working for some reason
            finalSkillList[doc2Idx[docIdx]] = sortDist


    skillScore = getSkillScore(model, docLines, doc2Idx, finalSkillList, querySkill, notFound)

    logger.info("skill Score %s", skillScore)

    ret = {}

    for id in finalSkillList:
        ret[id] = {
            "skill" : finalSkillList[id],
            "score" : skillScore[id],
            "debug" : {
                "avg_closest_dist" : avg_closest_dist,
                "max_closest_dist" : max_closest_dist,
                "findSkills" : findSkills
            }
            
        }

    return ret


def getSkillScore(model, docLines, doc2Idx, finalSkillList, querySkill, notFoundWords):


    finalResult = {}
    for docIndex in docLines:
        finalResult[doc2Idx[docIndex]] = {}
        for lineIdx, line in enumerate(docLines[docIndex]):
            for word in line:
                if word.lower() in notFoundWords:
                    finalResult[doc2Idx[docIndex]][word] = {
                        word: 0
                    }

        for qskill in querySkill:
            qskillvec = querySkill[qskill]
            finalResult[doc2Idx[docIndex]][qskill] = {}
            if doc2Idx[docIndex] in finalSkillList:
                for skill in finalSkillList[doc2Idx[docIndex]]:
                    org_dist = finalSkillList[doc2Idx[docIndex]][skill]
                    foundSkillVec = model.wv.get_vector(skill)
            
                    dist = cosine(qskillvec, foundSkillVec)

                    finalResult[doc2Idx[docIndex]][qskill][skill] = dist
            else:
                finalSkillList[doc2Idx[docIndex]] = {}

    return finalResult





def getWordMatrix(docLines, model):
    word2Vec = {}
    word2Idx = {}
    word2Line = {}
    word2Doc = {}

    for docIndex in docLines:
        for lineIdx, line in enumerate(docLines[docIndex]):
            for word in line:
                try:
                    word2Vec[word] = model.wv.get_vector(word) # mapping word to vector
                    word2Idx[len(word2Vec) - 1] = word # mapping index to work i.e 0,1,2
                    word2Line[len(word2Vec) - 1] = lineIdx # mapping index to line No
                    word2Doc[len(word2Vec) - 1] = docIndex # mapping index to document index
                except KeyError:
                    continue

    logger.info("total lines %s", len(word2Vec))
    data_matrix  = numpy.zeros( (len(word2Vec), 300), dtype='float32')

    for idx, key in enumerate(word2Vec):
        data_matrix[idx] = word2Vec[key]

    return data_matrix, word2Vec, word2Idx, word2Line, word2Doc

def queryMatrix(model, findSkills , isGeneric = False) :
    
    # findSkills = vectorizer.get_feature_names()

    querySkill = {}
    skillVec = []
    notFound = []
    for skill in findSkills:
        try:
            querySkill[skill] = model.wv.get_vector(skill)
            skillVec.append(model.wv.get_vector(skill))
        except KeyError:
            try:
                skill = skill.lower()
                querySkill[skill] = model.wv.get_vector(skill)
                skillVec.append(model.wv.get_vector(skill))
            except KeyError:
                notFound.append(skill.lower())
                continue

    query_matrix = numpy.zeros( (len(querySkill), 300), dtype='float32')
    for idx, key in enumerate(querySkill):
        query_matrix[idx] = querySkill[key]
    return query_matrix , skillVec, querySkill, notFound


from app.account import initDB, connect_redis, r_set, r_get, r_exists

def getSampleData(mongoid, account_name, account_config):
    docLines = {}
    db = initDB(account_name, account_config)    
    r = connect_redis(account_name, account_config)

    domain = None
    logger.critical("getting sample for %s", mongoid)
    data = None
    if "all" in mongoid:
        limit = 50
        # if more than 50. even faiss search also doesn't work properly
        mongoid = mongoid.replace("all:", "")
        if ":" in mongoid:
            skip = int(mongoid[mongoid.index(":")+1:])
            mongoid = mongoid[:mongoid.index(":")]
        else:
            skip = 0

        fetch_mongo = True

        job_row = db.jobprofiles.find_one({
            "_id": ObjectId(mongoid)
        })         

        if job_row:
            if "domain" in job_row:
                domain = job_row["domain"]

        if r_exists("job_" + mongoid, account_name, account_config) and False:
            logger.critical("data from redis")
            data = r_get("job_" + mongoid, account_name, account_config)
            # logger.critical("data from redis %s", data)
            dataMap = json.loads(data)
            data = []
            for key in dataMap:
                data.append(dataMap[key])

            
            if len(data) != 0:
                fetch_mongo = False

            data = data[skip:skip+limit]
                
            logger.critical("candidate full data found %s", len(data))
        if fetch_mongo:
            

            logger.critical("final mongo id %s", mongoid)
            logger.critical("skip %s", skip)
            ret = db.emailStored.find({ "job_profile_id": mongoid, "cvParsedInfo.debug" : {"$exists" : True} } , {"cvParsedInfo":1, "_id" : 1}).limit(limit).skip(skip)
            
            data = []
            for row in ret:
                row["_id"] = str(row["_id"])
                data.append(row)

    elif "," in mongoid:
        mongoid = mongoid.split(",")

        data = []
        for mid in mongoid:
            if r_exists(mid, account_name, account_config) and False:
                logger.critical("data from redis")
                row = r_get(mid, account_name, account_config)
                data.append(json.loads(row))
            else:
                logger.critical("data from mongo")
                row = db.emailStored.find_one({ 
                    "_id" : ObjectId(mid)
                })
                row["_id"] = str(row["_id"])
                r_set(mid, json.dumps(row, default=str), account_name, account_config)
                data.append(row)

            
    else:
        if r_exists(mongoid, account_name, account_config) and False:
            logger.critical("data from redis")
            row = json.loads(r_get(mongoid, account_name, account_config))
            data = [row]
        else:
            logger.critical("data from mongo")
            row = db.emailStored.find_one({ 
                "_id" : ObjectId(mongoid)
            })
            if row:
                row["_id"] = str(row["_id"])
                data = [row]
                r_set(mongoid, json.dumps(row, default=str), account_name, account_config)
        
        if len(data) > 0:
            row = data[0]
            if "job_profile_id" in row:
                if len(row["job_profile_id"]) > 0:
                    job_row = db.jobprofiles.find_one({
                        "_id": ObjectId(row["job_profile_id"])
                    })         

                    if job_row:
                        logger.critical(job_row)
                        if "domain" in job_row:
                            domain = job_row["domain"]
            # this is call mostly via resume processing microserver
            # we need to check if newcomproseedcontent is already tokenized and if not tokenize it
            # and save it to db and update redis cache if it already exists in redis else not
            # this will slove the speed issue 
            if "cvParsedInfo" in row:
                if "newCompressedStructuredContent" in row["cvParsedInfo"]:
                    cvParsedInfo = row["cvParsedInfo"]    
                    if "hasTokenized_newCompressedStructuredContent" not in cvParsedInfo:
                        for page in cvParsedInfo["newCompressedStructuredContent"]:
                            for line_idx, line in enumerate(cvParsedInfo["newCompressedStructuredContent"][page]):
                                doc = nlp(line["line"].lower())
                                token_line = [d.text for d in doc]
                                cvParsedInfo["newCompressedStructuredContent"][page][line_idx]["token_line"] = token_line

                        cvParsedInfo["hasTokenized_newCompressedStructuredContent"] = True
                        db.emailStored.update_one({ 
                            "_id" : ObjectId(mongoid)
                        }, {
                            "$set" : {
                                "cvParsedInfo" : cvParsedInfo
                            }
                        })
                        row["cvParsedInfo"] = cvParsedInfo
                        r_set(mongoid, json.dumps(row, default=str), account_name, account_config)

        


    logger.critical("processing data")    

    doc2Idx = {}
    total_documents = 0
    shouldTokenize = True

    if not data:
        return [], 0, None

    if len(data) > 50:
        shouldTokenize = False

    for docIndex, row in enumerate(data):
        docLines[docIndex] = []
        doc2Idx[docIndex] = row["_id"]
        if "cvParsedInfo" not in row:
            logger.critical("data not proper cvParsedInfo missing")
            continue
        
        if "newCompressedStructuredContent" not in row["cvParsedInfo"]:
            logger.critical("data not proper newCompressedStructuredContent cvParsedInfo missing")
            continue
        
        
        total_documents += 1

        cvParsedInfo = row["cvParsedInfo"]
        isSearchSpaceFound = False
        if account_name == "devrecruit":
            
            if "qa_parse_resume" in cvParsedInfo:
                for search_key in cvParsedInfo["qa_parse_resume"]:
                    
                    if search_key == "skills" or "exp_" in search_key or "certifications" == search_key or "training" == search_key or "summary" == search_key: 
                        isSearchSpaceFound = True
                        for row in cvParsedInfo["qa_parse_resume"][search_key]:
                            if "sentence" in row:
                                for line in row['sentence']:
                                    doc = nlp(line.lower())
                                    line = [d.text for d in doc]
                                        
                                    ngrams = generate_ngrams(" ".join(line), 3)
                                    ngrams.extend(generate_ngrams(" ".join(line), 2))
                                    line.extend(["_".join(n.split(" ")) for n in ngrams])
                                    docLines[docIndex].append(line)

            if "qa_fast_search_space" in cvParsedInfo and not isSearchSpaceFound:
                
                for search_key in cvParsedInfo["qa_fast_search_space"]:
                    
                    if search_key == "skills" or "exp_" in search_key or "certifications" == search_key or "training" == search_key or "summary" == search_key: 
                        skills = cvParsedInfo["qa_fast_search_space"][search_key]
                        isSearchSpaceFound = True
                        
                        line = skills["line"]
                        doc = nlp(line.lower()) #this is making slower for large data
                        line = [d.text for d in doc]
                            
                        ngrams = generate_ngrams(" ".join(line), 3)
                        ngrams.extend(generate_ngrams(" ".join(line), 2))
                        line.extend(["_".join(n.split(" ")) for n in ngrams])
                        docLines[docIndex].append(line)

        if not isSearchSpaceFound:
            for page in cvParsedInfo["newCompressedStructuredContent"]:
                for line in cvParsedInfo["newCompressedStructuredContent"][page]:

                    if "classify" not in line:
                        line["classify"] = ""

                    if isinstance(line["classify"], list):
                        line["classify"] = line["classify"][0]

                    # if line["classify"] == "CONTACT" or line["classify"] == "EDU" or line["classify"] == "ENDINFO":
                        # continue 
                        # pass

                    # logger.critical(line["classify"])
                    # logger.critical(line["line"])

                    if "token_line" in line:
                        line = line["token_line"] #pretokenize and save to db
                    else:
                        logger.critical("token line found. this should not happen")
                        if shouldTokenize:
                            doc = nlp(line["line"].lower()) #this is making slower for large data
                            line = [d.text for d in doc]
                        else:
                            line = line["line"].lower().split(" ")
                        
                    ngrams = generate_ngrams(" ".join(line), 3)
                    ngrams.extend(generate_ngrams(" ".join(line), 2))

                    line.extend(["_".join(n.split(" ")) for n in ngrams])
                    docLines[docIndex].append(line)

    logger.critical("total documents %s", total_documents)
    # logger.critical(doc2Idx)
    return docLines , total_documents, doc2Idx, domain


def get_job_criteria(mongoid,account_name, account_config):
    job_profile_id = None
    job_criteria_map = {}

    if ObjectId.is_valid(mongoid):
        db = initDB(account_name, account_config)

        job_profile_rows = db.jobprofiles.find({
            # "active_status": True
        }) 
        for job_profile_row in job_profile_rows:
            critera = {}
            if "criteria" in job_profile_row:
                critera = job_profile_row["criteria"]
                if critera is None:
                    continue
                if "requiredFormat" in critera:
                    continue

            job_criteria_map[str(job_profile_row["_id"])] = critera

        row = db.emailStored.find_one({
            "_id" : ObjectId(mongoid)
        })
        if row:
            if "job_profile_id" in row:
                job_profile_id = row['job_profile_id']
                if len(job_profile_id) == 0:
                    job_profile_id = None



    return job_profile_id, job_criteria_map