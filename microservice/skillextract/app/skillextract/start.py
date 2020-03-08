from app.logging import logger
from pymongo import MongoClient
import json
import random 

from scipy.spatial.distance import cosine

import numpy

import re
import os

from app.util import generate_ngrams

from app.skillsword2vec.start import loadModel

import spacy
nlp = spacy.load('en')

from bson.objectid import ObjectId

import redis
r = redis.Redis(host=os.environ.get("REDIS_HOST","redis"), port=os.environ.get("REDIS_PORT",6379), db=0)


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

def start(findSkills, mongoid, isGeneric = False):
    docLines, total_documents, doc2Idx = getSampleData(mongoid)

    if total_documents == 0:
        logger.info("not docs found")
        return

    logger.info("skills %s", findSkills)

    model = loadModel()
    data_matrix, word2Vec, word2Idx, word2Line, word2Doc = getWordMatrix(docLines, model)

    
    index_time_params = {'M': M, 'indexThreadQty': num_threads, 'efConstruction': efC, 'post' : 2}
    # logger.info('Index-time parameters %s', index_time_params)


    # Intitialize the library, specify the space, the type of the vector and add data points 
    index = nmslib.init(method='hnsw', space=space_name, data_type=nmslib.DataType.DENSE_VECTOR) 
    index.addDataPointBatch(data_matrix)

    start = time.time()
    index_time_params = {'M': M, 'indexThreadQty': num_threads, 'efConstruction': efC}
    index.createIndex(index_time_params) 
    end = time.time() 
    # logger.info('Index-time parameters %s', index_time_params)
    # logger.info('Indexing time = %f' % (end-start))

    # index.saveIndex('dense_index_optim.bin')

    # newIndex = nmslib.init(method='hnsw', space=space_name, data_type=nmslib.DataType.DENSE_VECTOR) 
    # newIndex.loadIndex('dense_index_optim.bin')

    
    query_time_params = {'efSearch': efS}
    # logger.info('Setting query-time parameters %s', query_time_params)
    index.setQueryTimeParams(query_time_params)


    #generate query matrix


    query_matrix, skillVec, querySkill = queryMatrix(model, findSkills)

    query_qty = query_matrix.shape[0]
    logger.info("query qty: %s", query_qty)

    avg_dist = 0
    avg_count = 0
    max_dist = 0
    closest_dist = 0
    max_closest_dist  = 0

    logger.info(skillVec)

    if len(skillVec) == 0:
        return "empty skills"

    for idx, vec in enumerate(skillVec):
        top1 = model.wv.most_similar(positive=[findSkills[idx]] , topn=1)
        closest_dist += top1[0][1]
        if top1[0][1] > max_closest_dist:
            max_closest_dist = top1[0][1]

        for idx2, vec2 in enumerate(skillVec):
            if idx2 <= idx:
                continue

            dist = cosine(vec.reshape(-1,1), vec2.reshape(-1,1))
            avg_dist += dist
            avg_count += 1
            if dist > max_dist:
                max_dist = dist


    avg_closest_dist = closest_dist/len(findSkills)
    if avg_count != 0:
        logger.info("avg distance between query words %s", avg_dist/avg_count)
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

            if distance <= maxDistSkillThresh:
                
                logger.info("max dist thresh skill: %s dist: %s word: %s", skill, maxDistSkillThresh, word2Idx[wordIdx])

                if orgDocIdx not in maxSkillDistCount:
                    maxSkillDistCount[orgDocIdx] = {}

                if orgLineIdx not in maxSkillDistCount[orgDocIdx]:
                    maxSkillDistCount[orgDocIdx][orgLineIdx] = {}
                
                if skill not in maxSkillDistCount[orgDocIdx][orgLineIdx]:
                    maxSkillDistCount[orgDocIdx][orgLineIdx][skill] = []

                maxSkillDistCount[orgDocIdx][orgLineIdx][skill].append( (wordIdx, distance) )


    # print(documents)
    # print(maxSkillDistCount)

    finalSkillList = {}

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


            sortDist = {k: v for k, v in sorted(sortDist.items(), key=lambda item: item[1]) }
            logger.info(sortDist)
            finalSkillList[doc2Idx[docIdx]] = sortDist

    return finalSkillList


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
    for skill in findSkills:
        try:
            querySkill[skill] = model.wv.get_vector(skill)
            skillVec.append(model.wv.get_vector(skill))
        except KeyError:
            continue

    query_matrix = numpy.zeros( (len(querySkill), 300), dtype='float32')
    for idx, key in enumerate(querySkill):
        query_matrix[idx] = querySkill[key]
    return query_matrix , skillVec, querySkill

def getSampleData(mongoid):
    docLines = {}

    client = MongoClient(os.environ.get("RECRUIT_BACKEND_DB" , "mongodb://176.9.137.77:27017/hr_recruit_dev"))
    db = client[os.environ.get("RECRUIT_BACKEND_DATABASe" , "hr_recruit_dev")]
    

    logger.info("getting sample for %s", mongoid)
    
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
            data = json.loads(data)
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
            row["_id"] = str(row["_id"])
            data = [row]
            r.set(mongoid, json.dumps(row, default=str))

    logger.info("processing data")    

    doc2Idx = {}
    total_documents = 0
    shouldTokenize = True

    if len(data) > 50:
        shouldTokenize = False

    for docIndex, row in enumerate(data):
        docLines[docIndex] = []
        doc2Idx[docIndex] = row["_id"]
        if "cvParsedInfo" not in row:
            logger.info("data not proper cvParsedInfo missing")
            continue
        else:
            if "debug" not in row["cvParsedInfo"]:
                logger.info("data not proper debug missing")
                continue
        
        
        total_documents += 1

        for page in row["cvParsedInfo"]["debug"]["compressedStructuredContent"]:
            for line in row["cvParsedInfo"]["debug"]["compressedStructuredContent"][page]:
                if "classify" not in line:
                    line["classify"] = ""

                if isinstance(line["classify"], list):
                    line["classify"] = line["classify"][0]

                # if line["classify"] == "CONTACT" or line["classify"] == "EDU" or line["classify"] == "ENDINFO":
                    # continue 
                    # pass

                # logger.info(line["classify"])
                # logger.info(line["line"])

                if shouldTokenize:
                    doc = nlp(line["line"].lower()) #this is making slower for large data
                    line = [d.text for d in doc]
                else:
                    line = line["line"].lower().split(" ")
                    
                ngrams = generate_ngrams(" ".join(line), 3)
                ngrams.extend(generate_ngrams(" ".join(line), 2))
                line.extend(["_".join(n.split(" ")) for n in ngrams])
                docLines[docIndex].append(line)

    logger.info("total documents %s", total_documents)
    # logger.info(doc2Idx)
    return docLines , total_documents, doc2Idx


