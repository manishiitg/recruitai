from transformers import (WEIGHTS_NAME,
                                  DistilBertConfig,
                                  DistilBertForSequenceClassification,
                                  DistilBertTokenizer)


import os
import torch                                
import random 
import numpy as np
import torch.functional as F

from app.config import RECRUIT_BACKEND_DB, RECRUIT_BACKEND_DATABASE

from app.config import BASE_PATH
from app.logging import logger
import json
from pymongo import MongoClient

from bson.objectid import ObjectId


model = None
tokenizer = None
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

BASE_MODEL_PATH = BASE_PATH + "/../pretrained/candidateclassify/distilbert"

label_list = []

db = None

def process(candidate_id):
    lines = getCandidateLines(candidate_id)
    if len(lines) == 0:
        db.emailStored.update_one({
        "_id" : ObjectId(candidate_id),
        }, {
            "$set" : {
                "candidateClassify" : {
                    "error" : "no relevent data found"
                } 
            }
        })
        return 0, False
    else:
        prob, label =  predict(lines[0])
        db.emailStored.update_one({
        "_id" : ObjectId(candidate_id),
        }, {
            "$set" : {
                "candidateClassify" : {
                    "probability" : str(prob),
                    "label" : label
                } 
            }
        })
        return prob, label
    pass

def initDB():
    global db
    if db is None:
        client = MongoClient(RECRUIT_BACKEND_DB) 
        db = client[RECRUIT_BACKEND_DATABASE]

    return db

def getCandidateLines(candidate_id):
    db = initDB()
    ret = db.emailStored.find({
        "_id" : ObjectId(candidate_id),
        'cvParsedInfo.newCompressedStructuredContent': {"$exists": True}
    })

    candidates = []


    for row in ret:
        wrklines = []
        alllines = []
        if "newCompressedStructuredContent" in row["cvParsedInfo"]:    
            for page in row["cvParsedInfo"]["newCompressedStructuredContent"]:
                for pagerow in row["cvParsedInfo"]["newCompressedStructuredContent"][page]:
                    line = pagerow["line"]
                    if len(line) == 0:
                        continue

                    if "classify" in pagerow:
                        classify = pagerow["classify"]
                        if classify == "WRK" or classify == "WRKEXP":
                            wrklines.append(line)
                            alllines.append(line)

                        if classify == "SUMMARY" or classify == "NOENTITY":
                            alllines.append(line)

                    elif "classifyNN" in pagerow and pagerow["classifyNN"] is not False:  
                        classifyNN = pagerow["classifyNN"]
                    
                        if classifyNN[0] == "WRK":
                            wrklines.append(line)
                            alllines.append(line)

                        if classifyNN[0] == "SUMMARY" or classifyNN[0] == "NOENTITY":
                            alllines.append(line)





    if len(wrklines) == 0:
        if len(alllines) == 0:
            logger.info("no data at all!!!!!")
        else:
            candidates.append(" ".join(alllines))
    else:
        candidates.append(" ".join(wrklines))

    return candidates


def predict(text):

    prob = torch.nn.Softmax()
    max_p = 0
    max_label = False
    with torch.no_grad():
        if len(text.split(" ")) < 10:
            return False

        if len(text) >= 512:
            text = text[:512]

        input_ids = torch.tensor(tokenizer.encode(text, add_special_tokens=True)).unsqueeze(0)  # Batch size 1
        # print(input_ids)
        labels = torch.tensor([1]).unsqueeze(0)  # Batch size 1
        outputs = model(input_ids.to(device), labels=labels.to(device))
        loss, logits = outputs[:2]

        
        probablity = prob(logits).squeeze().detach().cpu().numpy()
        # print(probablity)

        

        final_preds = []

        for index, p in enumerate(probablity):
            if p > .5:
                final_preds.append((p, label_list[index]))

        pred_index = np.argmax(logits.detach().cpu().numpy())

        # print(preds)

        
        logger.info("===================")
        # print(encoded.original_str)
        logger.info(text)
        
        

        if len(final_preds) > 1:
            for (p, label) in final_preds:
                logger.info("predicted %s with probablity %s", label , p)
                if p > max_p:
                    max_p = p
                    max_label = label
        else:
            logger.info("%s == %s", label_list[pred_index], probablity[pred_index])
            max_label = label_list[pred_index]
            max_p = probablity[pred_index]
        
        logger.info("===================")

    return max_p, max_label

def loadModel():
    global model
    global tokenizer
    global label_list
    if not model:
        do_eval = True
        args = {}

        with open(BASE_MODEL_PATH + '/labels.json') as f:
            label_list = json.load(f)
            logger.info("labels found %s", label_list)

        model_class = DistilBertForSequenceClassification
        tokenizer_class = DistilBertTokenizer

        args["lower_case"] = True
        args["output_dir"] = os.path.join(BASE_MODEL_PATH)

        tokenizer = tokenizer_class.from_pretrained(args["output_dir"], do_lower_case=args["lower_case"])   
        model = model_class.from_pretrained(args["output_dir"])
        model.to(device)

    return model, tokenizer