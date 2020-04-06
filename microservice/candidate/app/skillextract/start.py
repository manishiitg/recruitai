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

import random

from app.account import initDB

def start(domain, mongoid, isGeneric = True, account_name = "", account_config = {}):
    
    db = initDB(account_name, account_config)
    row = db.emailStored.find_one({ "_id" : ObjectId(mongoid) })
    
    words = []

    lines = []
    wordLines = []
    
    if "newCompressedStructuredContent" in row["cvParsedInfo"]:    
        for page in row["cvParsedInfo"]["newCompressedStructuredContent"]:
            for pagerow in row["cvParsedInfo"]["newCompressedStructuredContent"][page]:
                line = pagerow
                if "classify" not in line:
                    # in fast we won't have matched
                    # if line["matched"]:
                    #     print("some problem!!!!!!!!!!!!!!!!!!!!!")
                    
                    line["classify"] = ""

                if isinstance(line["classify"], list):
                    line["classify"] = line["classify"][0]

                if line["classify"] == "CONTACT" or line["classify"] == "EDU" or line["classify"] == "ENDINFO":
                    continue 
                    # pass

                lines.append(line["line"].lower())
                doc = nlp(line["line"].lower())
                words.extend( [d.text for d in doc]  )
                wordLines.append([d.text for d in doc] )



    model, features = loadModel(domain)

    # generic means we are search for full feature names instead of specific skills


    skillsFound = []

    globalSkillDist = {}


    distThresh = 0 # .5
    maxDistSkillThresh = 0 # max_dist . 7

    all_skills = []
    for line in wordLines:
        vecFound = []
        ngrams = generate_ngrams(" ".join(line), 3)
        ngrams.extend(generate_ngrams(" ".join(line), 2))
        line.extend(["_".join(n.split(" ")) for n in ngrams])

        newline = []
        newline.extend(line)
        newline.extend(["_".join(n.split(" ")) for n in ngrams])
        for word in newline:

            try:
                model.wv.get_vector(word)
                vecFound.append(word)
            except KeyError:
                pass

        vecFound = list(set(vecFound))

        if len(vecFound) > 1:

            # print(vecFound)

            tensor = numpy.zeros( (len(vecFound), 300), dtype='float32')
            for i, word in enumerate(vecFound):

                try:
                    tensor[i] = model.wv.get_vector(word)
                except KeyError:
                    pass

            wordMap = {}
            for idx, vec in enumerate(tensor):
                if vecFound[idx] not in features:
                    continue

                wordMap[vecFound[idx]] = [  (vecFound[idx] , 0 , True)  ]
                for idx2, vec2 in enumerate(tensor):
                    if idx2 > idx:
                        dist = cosine(vec.reshape(-1,1), vec2.reshape(-1,1)) 
                        if dist < .75:
                            wordMap[vecFound[idx]].append( (vecFound[idx2] , dist , vecFound[idx] in features )  )

                if vecFound[idx] in wordMap:
                    if len(wordMap[vecFound[idx]]) < 3:
                        del wordMap[vecFound[idx]]


            if len(wordMap):
                max_len = 0
                max_key = ""
                for key in wordMap:
                    if len(wordMap[key]) > max_len:
                        max_len = len(wordMap[key])
                        max_key = key



                print(wordMap[max_key])  
                skillsFound.append((wordMap[max_key]))


    db.emailStored.update_one({ "_id" : ObjectId(mongoid) }, 
    {
        "$set" : {
            "candidateClassify.all_skills" : skillsFound
        }
    })

    return skillsFound