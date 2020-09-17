from transformers import BartTokenizer, BartForConditionalGeneration, pipeline
import torch
from app.logging import logger

torch_device = 'cuda' if torch.cuda.is_available() else 'cpu'

model = None
tokenizer = None
summarizer = None

from app.publishdatasync import sendMessage as datasync

from pdfminer.pdfpage import PDFTextExtractionNotAllowed

from pdfminer.high_level import extract_text
from app.config import BASE_PATH
import os
from pymongo import MongoClient
from bson.objectid import ObjectId
import time
import traceback

from app.account import initDB, get_cloud_bucket , connect_redis

from pathlib import Path

import sys
from app.config import storage_client
import subprocess


def process(filename, mongoid, account_name, account_config):

    # db = initDB(account_name, account_config)

    

    # if count > 0:
    #     logger.critical("summary exists so skipping")
    #     return "summary exists"


    # dest = BASE_PATH + "/../cvreconstruction/"

    # RESUME_UPLOAD_BUCKET = get_cloud_bucket(account_name, account_config)

    # bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
    # blob = bucket.blob(account_name + "/" + filename)

    # Path(dest).mkdir(parents=True, exist_ok=True)

    # try:
    #     blob.download_to_filename(os.path.join(dest, filename))
    #     logger.critical("file downloaded at %s", os.path.join(dest, filename))
    # except  Exception as e:
    #     logger.critical(str(e))
    #     traceback.print_exc(file=sys.stdout)
    #     return {"error" : str(e)}


    # dest = BASE_PATH + "/../cvreconstruction/"

    # if os.path.exists(os.path.join(dest, filename)):
    #     logger.critical("foudn the file")
    # else:
    #     return {"error" : "cv file not found"}

    # finalPdf = os.path.join(dest, filename)
    # content = ""

    # try:
    #     content = extract_text(finalPdf)
    #     content = str(content)
    # except PDFTextExtractionNotAllowed as e:
    #     logger.critical(e)
            
    #     logger.critical("skipping due to error in cv extration %s " , finalPdf)
    
    # except Exception as e:
        
    #     logger.critical("general exception in trying nodejs text cv extration %s %s " , str(e) , finalPdf)
    #     x = subprocess.check_output(['pdf-text-extract ' + finalPdf], shell=True , timeout=60)
    #     x = x.decode("utf-8") 
    #     # x = re.sub(' +', ' ', x)
    #     logger.critical(x)
    #     start = "[ '"
    #     end = "' ]"

    #     x = x.replace(start, "")
    #     x = x.replace(end, "")
    #     pages_data_extract = x.split("',")
    #     content = " ".join(pages_data_extract)

    # logger.critical(content)

    db = initDB(account_name, account_config)

    row = db.emailStored.find_one({
            "_id" : ObjectId(mongoid)
        })

    if not row:
        logger.critical("mongo id not found")
        return {"error" : "mongo id not found"}

    finalLines = []
    content = ""
    if "cvParsedInfo" in row:
        cvParsedInfo = row["cvParsedInfo"]
        if "newCompressedStructuredContent" in cvParsedInfo:
            for page in cvParsedInfo["newCompressedStructuredContent"]:
                for pagerow in cvParsedInfo["newCompressedStructuredContent"][page]:
                    if len(pagerow["line"]) > 0:
                        finalLines.append(pagerow["line"])

    content = " ".join(finalLines)

    if len(content) > 0:
        

        star_time = time.time()
        summary = extractSummary(content)
            
        logger.critical(summary)
        db = initDB(account_name, account_config)
        ret = db.emailStored.update_one({
            "_id" : ObjectId(mongoid)
        }, {
            "$set": {
                "aisummary": {
                    "text" : summary[0]["summary_text"],
                    "time" : time.time() - star_time
                }
            }
        })
        datasync({
            "id" : mongoid,
            "action" : "syncCandidate",
            "account_name" : account_name,
            "account_config" : account_config,
            "priority" : 10,
            "field" : "aisummary"
        })

        logger.critical("time taken $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ %s", time.time() - star_time)
    else:
        logger.critical("no content found for summary")
            

def extractSummary(text):
    # article_input_ids = tokenizer.batch_encode_plus([text], return_tensors='pt', max_length=1024)['input_ids'].to(torch_device)
    # summary_ids = model.generate(article_input_ids,
    #                             num_beams=4,
    #                             max_length=150,
    #                             early_stopping=True)

    # return " ".join([tokenizer.decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=False) for g in summary_ids])
    if len(text) >= 1024:
        text = text[:1024]
    return summarizer(text, min_length=5, max_length=150, num_beams=4, early_stopping=True)


from pathlib import Path

def loadModel():
    global model
    global tokenizer
    global summarizer
    # if model is None:

    #     if os.path.exists("/workspace/pretrained/bart/pytorch_model.bin"):
    #         tokenizer = BartTokenizer.from_pretrained('/workspace/pretrained/bart/')
    #         model = BartForConditionalGeneration.from_pretrained('/workspace/pretrained/bart/')
    #     else:
    # tokenizer = BartTokenizer.from_pretrained('bart-large-cnn')
    # model = BartForConditionalGeneration.from_pretrained('bart-large-cnn')
    # Path("/workspace/pretrained/bart").mkdir(parents=True, exist_ok=True)
    # model.save_pretrained("/workspace/pretrained/bart")
    # tokenizer.save_pretrained("/workspace/pretrained/bart")

    logger.critical("gpu %s", torch.cuda.is_available())
    if torch.cuda.is_available():
        summarizer = pipeline("summarization" , model="facebook/bart-large-cnn", device=0)
    else:
        summarizer = pipeline("summarization" , model="facebook/bart-large-cnn")
        
    # summarizer = pipeline("summarization" , model="sshleifer/distilbart-cnn-12-6")
    
    return model, tokenizer, summarizer