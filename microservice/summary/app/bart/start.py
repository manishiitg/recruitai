from app.account import initDB, get_cloud_bucket, connect_redis
import subprocess
import sys
from pathlib import Path
import traceback
import time
from bson.objectid import ObjectId
from pymongo import MongoClient
import os
from app.config import BASE_PATH
from app.publishdatasync import sendMessage as datasync
from transformers import BartTokenizer, BartForConditionalGeneration, pipeline
import torch
from app.logging import logger
import json
import requests

torch_device = 'cuda' if torch.cuda.is_available() else 'cpu'

model = None
tokenizer = None
summarizer = None
summarizer_fast = None


# from pdfminer.pdfpage import PDFTextExtractionNotAllowed
# from pdfminer.high_level import extract_text


# from app.config import storage_client


def process(filename, mongoid, priority, account_name, account_config):

    db = initDB(account_name, account_config)

    row = db.emailStored.find_one({
        "_id": ObjectId(mongoid)
    })

    if not row:
        logger.critical("mongo id not found")
        return {"error": "mongo id not found"}

    if "aisummary" in row:
        logger.critical("summary already exists")
        return {"error": "already summary exists"}

    if "subject" in row:
        subject = row["subject"]
        if subject:
            if "manually" in subject:
                # even if priority between 2-4 summary will be generated for manual candidates
                priority = priority + 5

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
        summary = extractSummary(content, priority)

        if summary:
            logger.critical(summary)
            db = initDB(account_name, account_config)
            ret = db.emailStored.update_one({
                "_id": ObjectId(mongoid)
            }, {
                "$set": {
                    "aisummary": {
                        "text": summary[0]["summary_text"],
                        "time": time.time() - star_time
                    }
                }
            })
            datasync({
                "id": mongoid,
                "action": "syncCandidate",
                "account_name": account_name,
                "account_config": account_config,
                "priority": 10,
                "field": "aisummary"
            })

            logger.critical("time taken $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ %s priority %s", time.time(
            ) - star_time, priority)
    else:
        logger.critical("no content found for summary")


def extractSummary(text, priority, api=False):
    if len(text) >= 1024:
        text = text[:1024]
    if api:
        API_TOKEN = os.getenv("HUGGINGFACE_INTERFACE_API", "")
        logger.info("huggingface inference token %s", API_TOKEN)
        # API_URL = "https://api-inference.huggingface.co/models/sshleifer/distilbart-cnn-12-6"
        API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
        headers = {"Authorization": f"Bearer {API_TOKEN}"}

        def query(payload):
            data = json.dumps(payload)
            response = requests.request(
                "POST", API_URL, headers=headers, data=data)
            return json.loads(response.content.decode("utf-8"))

        data = query({
            "inputs": text,
            "wait_for_model": True
        })

        # print(data)
        if "error" in data:
            return extractSummary(text, priority, False)
        else:
            return data

    # article_input_ids = tokenizer.batch_encode_plus([text], return_tensors='pt', max_length=1024)['input_ids'].to(torch_device)
    # summary_ids = model.generate(article_input_ids,
    #                             num_beams=4,
    #                             max_length=150,
    #                             early_stopping=True)

    # return " ".join([tokenizer.decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=False) for g in summary_ids])

    # print(len(text))
    # 一攀攀爀愀樀 刀愀眀愀琀 圀攀戀 䐀攀猀椀最渀攀爀 匀攀攀欀椀渀最 愀渀 伀瀀瀀漀爀琀甀渀椀琀礀 琀漀 眀漀爀欀 愀猀 愀 䌀爀攀愀琀椀瘀攀 圀攀戀 䐀攀猀椀最渀攀爀 眀栀攀爀攀 䤀  挀愀渀 甀琀椀氀椀稀攀 洀礀 䐀椀最椀琀愀氀 䴀愀爀欀攀琀椀渀最 愀渀搀 眀攀戀 搀攀猀椀最渀椀渀最 猀欀椀氀氀 琀漀眀愀爀搀猀 琀栀攀  最爀漀眀琀栀 愀渀搀 䐀攀瘀攀氀漀瀀洀攀渀琀 漀昀 琀栀攀 漀爀最愀渀椀稀愀琀椀漀渀⸀ 䔀搀甀挀愀琀椀漀渀 ㄀　琀栀 䌀氀愀猀猀 䠀⸀䈀⸀匀⸀䔀 䈀漀爀愀搀 ㄀㈀琀栀 䌀氀愀猀猀 䌀⸀䈀⸀匀⸀䔀 䈀漀爀愀搀 䜀爀愀搀甀愀琀椀漀渀 䐀攀氀栀椀 唀渀椀瘀攀爀猀椀琀礀 匀伀䰀  䔀砀瀀攀爀椀攀渀挀攀 䌀爀攀愀琀攀  愀渀搀 䴀愀渀愀最攀  圀攀戀猀椀琀攀 ㈀　㄀㌀ ⴀ ㈀　㄀㐀 ㈀　㄀㔀 ⴀ ㈀　㄀㘀 ㈀　㄀㘀 ⴀ ㈀　㄀㤀 匀欀椀氀氀 倀栀漀琀漀猀栀漀瀀 䌀漀爀愀氀 䐀爀愀眀 圀攀戀猀椀琀攀 䐀攀猀椀最渀椀渀最 䐀椀最椀琀愀氀 䴀愀爀欀攀琀椀渀最 　─ 　─  ─ 　─ 㔀　─ ㄀　　─ 㔀　─ ㄀　　─  㔀　─ ㄀　　─ 㔀　─ ㄀　　─ 倀爀漀昀椀氀攀 一愀洀攀 一攀攀爀愀樀 刀愀眀愀琀  䐀愀琀攀 漀昀 戀椀爀琀栀 䨀甀氀Ⰰ 　㜀Ⰰ ㄀㤀㤀㠀 䄀搀搀爀攀猀猀 䨀ⴀ㤀㄀戀Ⰰ 䰀愀氀 䬀甀愀渀Ⰰ 倀爀攀洀 一愀最愀爀 吀甀最栀氀愀欀愀戀愀搀 ⴀ ㄀㄀　　㐀㐀 倀栀漀渀攀 ⬀㤀㄀ 㜀㤀㠀㠀㤀㤀㠀㌀㈀㘀 䔀洀愀椀氀 渀攀攀爀愀樀爀愀眀愀琀㤀㌀㔀㔀䀀最洀愀椀氀⸀挀漀洀 匀漀挀椀愀氀 䰀椀渀欀 栀琀琀瀀猀㨀⼀⼀眀眀眀⸀昀愀挀攀戀漀漀欀⸀挀漀洀⼀ 渀攀攀爀愀樀⸀爀愀眀愀琀⸀㜀㔀㘀㠀㔀㤀㘀㈀ 圀漀爀欀 䔀砀瀀攀爀椀攀渀挀攀 ㄀ 夀攀愀爀 䔀砀瀀攀爀椀攀渀挀攀  䐀椀最椀 䤀渀昀漀礀攀挀栀 椀渀 㘀 洀漀渀琀栀 䄀爀琀栀 䤀渀猀琀椀琀甀琀攀 椀渀 㘀 洀漀渀琀栀  䄀猀 愀 圀攀戀 䐀攀猀椀最渀攀爀 圀漀爀欀 倀爀漀樀攀挀琀猀 䰀椀渀欀 眀眀眀⸀搀洀琀挀氀愀猀猀⸀挀漀洀 眀眀眀⸀瀀栀瀀琀爀愀椀渀椀渀最椀渀猀琀椀琀甀琀攀⸀椀渀 眀眀眀⸀樀愀瘀愀猀挀栀漀漀氀猀⸀椀渀 眀眀眀⸀眀攀戀搀攀猀椀最渀椀渀最椀渀猀琀椀琀甀琀攀⸀椀渀 眀眀眀⸀搀椀最椀椀渀昀漀琀攀挀栀⸀挀漀洀⸀愀甀 眀眀眀⸀最攀琀洀礀挀漀氀氀攀最攀⸀椀渀⼀瘀椀猀愀⼀ 眀眀眀⸀猀漀昀琀眀愀爀攀琀爀愀椀渀椀渀最椀渀猀琀椀琀甀琀攀⸀椀渀
    # something this is kind of things are coming and this fails

    try:
        if priority < 4:
            return None
        if priority < 6:
            return summarizer_fast(text)
        else:
            return summarizer(text, min_length=5, max_length=150, num_beams=4, early_stopping=True)
    except Exception as e:
        logger.critical(e)
        return None


def loadModel():
    global model
    global tokenizer
    global summarizer
    global summarizer_fast
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
    if summarizer is None:
        if torch.cuda.is_available():
            summarizer = pipeline(
                "summarization", model="facebook/bart-large-cnn", device=0)
        else:
            summarizer = pipeline(
                "summarization", model="facebook/bart-large-cnn")

    if summarizer_fast is None:
        if torch.cuda.is_available():
            summarizer_fast = pipeline(
                'summarization', model='sshleifer/distilbart-cnn-6-6')
        else:
            summarizer_fast = pipeline(
                'summarization', model='sshleifer/distilbart-cnn-6-6')

    # summarizer = pipeline("summarization" , model="sshleifer/distilbart-cnn-12-6")

    return model, tokenizer, summarizer
