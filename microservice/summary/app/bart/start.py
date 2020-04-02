from transformers import BartTokenizer, BartForConditionalGeneration
import torch
from app.logging import logger

from app.config import RESUME_UPLOAD_BUCKET

torch_device = 'cuda' if torch.cuda.is_available() else 'cpu'

model = None
tokenizer = None

from pdfminer.pdfpage import PDFTextExtractionNotAllowed

from pdfminer.high_level import extract_text
from app.config import BASE_PATH
import os
from pymongo import MongoClient
from bson.objectid import ObjectId
import time
import traceback

db = None
def initDB():
    global db
    if db is None:
        client = MongoClient(os.getenv("RECRUIT_BACKEND_DB")) 
        db = client[os.getenv("RECRUIT_BACKEND_DATABASE")]

    return db

from pathlib import Path

import sys
from app.config import storage_client


def process(filename, mongoid):

    dest = BASE_PATH + "/../cvreconstruction/"

    bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
    blob = bucket.blob(filename)

    Path(dest).mkdir(parents=True, exist_ok=True)

    try:
        blob.download_to_filename(os.path.join(dest, filename))
        logger.info("file downloaded at %s", os.path.join(dest, filename))
    except  Exception as e:
        logger.critical(str(e))
        traceback.print_exc(file=sys.stdout)
        return {"error" : str(e)}


    dest = BASE_PATH + "/../cvreconstruction/"

    if os.path.exists(os.path.join(dest, filename)):
        logger.info("foudn the file")
    else:
        return {"error" : "cv file not found"}

    finalPdf = os.path.join(dest, filename)
    content = ""

    try:
        content = extract_text(finalPdf)
        content = str(content)
    except PDFTextExtractionNotAllowed as e:
        logger.critical(e)
            
        logger.critical("skipping due to error in cv extration %s " , finalPdf)
    
    except Exception as e:
        
        logger.critical("general exception in trying nodejs text cv extration %s %s " , str(e) , finalPdf)
        x = subprocess.check_output(['pdf-text-extract ' + finalPdf], shell=True)
        x = x.decode("utf-8") 
        # x = re.sub(' +', ' ', x)
        logger.info(x)
        start = "[ '"
        end = "' ]"

        x = x.replace(start, "")
        x = x.replace(end, "")
        pages_data_extract = x.split("',")
        content = " ".join(pages_data_extract)

    logger.info(content)

    if len(content) > 0 and mongoid and ObjectId.is_valid(mongoid):
        star_time = time.time()
        summary = extractSummary(content)
        logger.info(summary)
        db = initDB()
        ret = db.emailStored.update_one({
            "_id" : ObjectId(mongoid)
        }, {
            "$set": {
                "aisummary": {
                    "text" : summary,
                    "time" : time.time() - star_time
                }
            }
        })
        logger.info("time taken $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ %s", time.time() - star_time)

def extractSummary(text):
    article_input_ids = tokenizer.batch_encode_plus([text], return_tensors='pt', max_length=1024)['input_ids'].to(torch_device)
    summary_ids = model.generate(article_input_ids,
                                num_beams=4,
                                max_length=150,
                                early_stopping=True)

    return " ".join([tokenizer.decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=False) for g in summary_ids])


def loadModel():
    global model
    global tokenizer
    if model is None:
        tokenizer = BartTokenizer.from_pretrained('bart-large-cnn')
        model = BartForConditionalGeneration.from_pretrained('bart-large-cnn')

    return model, tokenizer