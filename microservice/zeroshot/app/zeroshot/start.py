from transformers import pipeline
import torch
from app.logging import logger

torch_device = 'cuda' if torch.cuda.is_available() else 'cpu'

model = None
tokenizer = None
zeroshot = None
zeroshot_fast = None
import datetime

from app.publishdatasync import sendMessage as datasync

# from pdfminer.pdfpage import PDFTextExtractionNotAllowed
# from pdfminer.high_level import extract_text

from app.config import BASE_PATH
import os
from pymongo import MongoClient
from bson.objectid import ObjectId
import time
import traceback

from app.account import initDB, get_cloud_bucket , connect_redis

from pathlib import Path

import sys
# from app.config import storage_client
import subprocess
import requests

def process(text, labels, mongoid, notifyurl, priority, account_name, account_config, meta = {}):
    
    max_label, scores, labels =  classifyZeroShot(text, labels, priority)

    if notifyurl:
        logger.critical("notify url found %s", notifyurl)
        x = requests.post(notifyurl, data = {
            'text': text,
            "labels" : labels,
            "mongoid" : mongoid,
            "max_label" : max_label,
            "labels" : labels,
            "meta" : meta
        })
        logger.critical(x)

    if mongoid and ObjectId.is_valid(mongoid):
        logger.critical("mongoid %s", mongoid)
        db = initDB(account_name, account_config)

        row = db.emailStored.find_one({
                "_id" : ObjectId(mongoid)
            })

        if not row:
            logger.critical("mongo id not found")
            return {"error" : "mongo id not found"}

        db.emailStored.update_one({
            "_id" : ObjectId(mongoid)
        }, {
            "$set" : {
                "cvParsedInfo.zeroshot" : {
                    "text" : text,
                    "labels" : labels,
                    "max_label" : max_label,
                    "scores" : scores,
                    "time" : datetime.datetime.now()
                }
            }
        })

    return max_label
            

def classifyZeroShot(text, labels, priority):
    if len(text) >= 256:
        text = text[:256]

    global zeroshot

    logger.critical("text :%s", text)
    logger.critical("labels :%s", labels)

    classify = zeroshot(text, labels)   
    scores = classify["scores"] 
    labels = classify["labels"]

    logger.critical("labels :%s", labels)
    logger.critical("scores :%s", scores)

    max_score = 0
    max_label = ""
    for idx, score in enumerate(scores):
        if score > max_score:
            max_score = score
            max_label = labels[idx]

    logger.critical("max_label :%s", max_label)
    return max_label, scores, labels
    
    # except Exception as e:
    #     logger.critical(e)
    #     return None
    


from pathlib import Path

def loadModel():
    global model
    global tokenizer
    global zeroshot
    global zeroshot_fast
    
    logger.critical("gpu %s", torch.cuda.is_available())
    if zeroshot is None:
        if torch.cuda.is_available():
            zeroshot = pipeline("zero-shot-classification", device=0)
        else:
            zeroshot = pipeline("zero-shot-classification")
    
    if zeroshot_fast is None and False:
        if torch.cuda.is_available():
            zeroshot_fast = pipeline('zero-shot-classification', model='valhalla/distilbart-mnli-12-3')
        else:
            zeroshot_fast = pipeline('zero-shot-classification', model='valhalla/distilbart-mnli-12-3')
        
    
    return model, tokenizer, zeroshot