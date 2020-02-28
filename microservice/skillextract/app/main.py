from app.logging import logger
from pymongo import MongoClient
import json
import random 

from scipy.spatial.distance import cosine

import numpy

import re

from app.util import generate_ngrams

from app.skillsword2vec.start import loadModel

import spacy
nlp = spacy.load('en')

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

def start(isGeneric = False):
    findSkills = ["python", "machine_learning"]
    docLines, total_documents = getSampleData()

    if total_documents == 0:
        logger.info("not docs found")
        return

    model = loadModel()
    data_matrix, word2Vec, word2Idx, word2Line, word2Doc = getWordMatrix(docLines, model)

    
    index_time_params = {'M': M, 'indexThreadQty': num_threads, 'efConstruction': efC, 'post' : 2}
    logger.info('Index-time parameters %s', index_time_params)


    # Intitialize the library, specify the space, the type of the vector and add data points 
    index = nmslib.init(method='hnsw', space=space_name, data_type=nmslib.DataType.DENSE_VECTOR) 
    index.addDataPointBatch(data_matrix)

    start = time.time()
    index_time_params = {'M': M, 'indexThreadQty': num_threads, 'efConstruction': efC}
    index.createIndex(index_time_params) 
    end = time.time() 
    logger.info('Index-time parameters %s', index_time_params)
    logger.info('Indexing time = %f' % (end-start))

    # index.saveIndex('dense_index_optim.bin')

    # newIndex = nmslib.init(method='hnsw', space=space_name, data_type=nmslib.DataType.DENSE_VECTOR) 
    # newIndex.loadIndex('dense_index_optim.bin')

    
    query_time_params = {'efSearch': efS}
    logger.info('Setting query-time parameters %s', query_time_params)
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
    logger.info("avg distance between query words %s", avg_dist/avg_count)
    logger.info("max distance %s", max_dist)
    logger.info("avg closest distance %s", avg_closest_dist)
    logger.info("max closest distance %s", max_closest_dist)
    
    start = time.time() 
    # assume 20 skills per doc which is already a lot 
    # avergae is 5 or 6
    nbrs = index.knnQueryBatch(query_matrix, k = 20 * total_documents, num_threads = num_threads)
    end = time.time() 
    print('kNN time total=%f (sec), per query=%f (sec), per query adjusted for thread number=%f (sec)' % 
        (end-start, float(end-start)/query_qty, num_threads*float(end-start)/query_qty))
    



    documents = {}

    wordIdx2Dist = {}


    distThresh = avg_closest_dist
    maxDistSkillThresh = max_closest_dist

    maxSkillDistCount = {}

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

                if orgDocIdx not in maxSkillDistCount:
                    maxSkillDistCount[orgDocIdx] = {}

                if orgLineIdx not in maxSkillDistCount[orgDocIdx]:
                    maxSkillDistCount[orgDocIdx][orgLineIdx] = {}
                
                if skill not in maxSkillDistCount[orgDocIdx][orgLineIdx]:
                    maxSkillDistCount[orgDocIdx][orgLineIdx][skill] = []

                maxSkillDistCount[orgDocIdx][orgLineIdx][skill].append( (wordIdx, distance) )


    # print(documents)
    # print(maxSkillDistCount)

    for docIdx in range(total_documents):
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

                        count = len(lines[orgLineIdx][skill])
                        # print("skills count" ,maxSkillCount, "actual count ", count)
                        if count > maxSkillCount or count > len(querySkill) * .5:
                        # len(vecFound) * .2
                        # print("line index ", orgLineIdx)
                            for idx in lines[orgLineIdx][skill]:
                                if word2Idx[idx] not in globalSkillDist:
                                    globalSkillDist[word2Idx[idx]] = {
                                        "dist" : wordIdx2Dist[skill][idx],
                                        "count" : 1
                                    }
                                else:
                                    globalSkillDist[word2Idx[idx]]["dist"] += wordIdx2Dist[skill][idx]
                                    globalSkillDist[word2Idx[idx]]["count"] += 1


                        # print(word2Idx[idx])

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
                if count >= query_qty * .5 and count > 1 :
                    if word not in globalSkillDist:
                        globalSkillDist[word] = {
                            "dist" : dist,
                            "count" : 1
                        }
                    else:
                        globalSkillDist[word]["dist"] += dist
                        globalSkillDist[word]["count"] += 1


                logger.info(word, "via broad skill match")
        

    

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


            sortDist = {k: v for k, v in sorted(sortDist.items(), key=lambda item: item[1])}
            logger.info(sortDist)
            documents[docIdx]["skills"] = sortDist

    return documents


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

def getSampleData():
    docLines = {}

    client = MongoClient("mongodb://176.9.137.77:27017/hr_recruit_dev")
    db = client.hr_recruit_dev
    ret = db.emailStored.find({ "cvParsedInfo.debug" : {"$exists" : True} }).limit(1)
    # .skip(skipInt).limit(1)
    # "file" : "da50ecdb-cbd4-4cf1-8d62-f15d47d645fe.pdf"
    # "file" : "55045-Neha_Resume.docx"


    data = []
    for row in ret:
        row["_id"] = str(row["_id"])
        data.append(row)

    logger.info(row)

    total_documents = len(data)

    for docIndex, row in enumerate(data):
        docLines[docIndex] = []
        if "debug" not in row["cvParsedInfo"]:
            logger.info("data not proper")
            continue

        for page in row["cvParsedInfo"]["debug"]["compressedStructuredContent"]:
            for line in row["cvParsedInfo"]["debug"]["compressedStructuredContent"][page]:
                if "classify" not in line:
                    line["classify"] = ""

                if isinstance(line["classify"], list):
                    line["classify"] = line["classify"][0]

                if line["classify"] == "CONTACT" or line["classify"] == "EDU" or line["classify"] == "ENDINFO":
                    # continue 
                    pass

                logger.info(line["classify"])
                logger.info(line["line"])
                doc = nlp(line["line"].lower())
                line = [d.text for d in doc]
                ngrams = generate_ngrams(" ".join(line), 3)
                line.extend(["_".join(n.split(" ")) for n in ngrams])
                docLines[docIndex].append(line)

    logger.info("total documents %s", total_documents)

    return docLines , total_documents

if __name__ == '__main__':
    start()