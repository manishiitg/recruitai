from app.nerclassify.start import process as classifyNer
from app.detectron.start import processAPI
from app.ner.start import processAPI as extractNer
# from app.picture.start import processAPI as extractPicture
from app.config import  BASE_PATH
from app.logging import logger
from app.config import storage_client
from pathlib import Path
import subprocess
import os
# from app.search.index import addDoc
import shutil  
import traceback

from threading import Thread

import json

from app.publishsearch import sendBlockingMessage
from app.publishgender import sendBlockingMessage as getGenderMessage

from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

import time

from pdfminer.pdfpage import PDFTextExtractionNotAllowed

from app.fast.start import process as processFast

import sys


from app.account import initDB, get_cloud_bucket, get_cloud_url

def fullResumeParsing(filename, mongoid=None, message = None , priority = 0, account_name = "", account_config = {}):
    try:


        init_timer = time.time()
        timer = time.time()

        dest = BASE_PATH + "/../cvreconstruction/"
        RESUME_UPLOAD_BUCKET = get_cloud_bucket(account_name, account_config)

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

        db = initDB(account_name, account_config)
        if mongoid and ObjectId.is_valid(mongoid):
            ret = db.emailStored.update_one({
                "_id" : ObjectId(mongoid)
            }, {
                "$set": {
                    "pipeline": [{
                        "stage" : 0,
                        "name": "started",
                        "start_time" : time.time()
                    }]
                }
            })

       
        fullResponse = {}
        dest = BASE_PATH + "/../cvreconstruction"
            
        timer = time.time()
        parsing_type = "full"
        if priority > 5 :
            parsing_type = "full"
        else:
            parsing_type = "fast"

        if message and "parsing_type" in message:
            parsing_type = message["parsing_type"]

        if parsing_type == "full":
            response, basePath, timeAnalysis = processAPI(os.path.join(dest, filename), account_name, account_config)

            logger.info("========================================== time analysis ==========================================")
            for fileIdx in timeAnalysis:
                logger.info("file idx %s" , fileIdx)
                for work in timeAnalysis[fileIdx]:
                    logger.info("================   work %s time taken %s ", work, timeAnalysis[fileIdx][work])


            logger.info("total time taken %s", (time.time() - timer))

            logger.info("========================================== time analysis ==========================================")
        else:
            response = processFast(os.path.join(dest, filename))
            timeAnalysis = {}

        if mongoid and ObjectId.is_valid(mongoid):
            ret = db.emailStored.update_one({
                "_id" : ObjectId(mongoid)
            }, {
                "$push": {
                    "pipeline": {
                        "stage" : 2,
                        "name": "resume_construction",
                        "timeAnalysis" : json.loads(json.dumps(timeAnalysis)),
                        "timeTaken": time.time() - timer,
                        "start_time" : time.time(),
                        # "debug" : {
                        #     "response": json.loads(json.dumps(response)), 
                        #     "basePath" : basePath
                        # }
                    }
                }
            })
            timer = time.time()

        finalLines = []
        for page in response:
            for pagerow in page["compressedStructuredContent"]:
                logger.info(pagerow)
                finalLines.append(pagerow["line"])

        if mongoid:
            t = Thread(target=addToSearch, args=(mongoid,finalLines,{}, account_name, account_config))
            t.start()
            # t.join()

            if mongoid and ObjectId.is_valid(mongoid):
                ret = db.emailStored.update_one({
                    "_id" : ObjectId(mongoid)
                }, {
                    "$push": {
                        "pipeline": {
                            "stage" : 3,
                            "name": "searchIdx",
                            "start_time" : time.time(),
                            "timeTaken": time.time() - timer
                        }
                    }
                })
            timer = time.time()

            # doing this with datasync now 
            pass

        # fullResponse["compressedContent"] = {"response" : response, "basePath" : basePath}

        nertoparse = []
        row = []
        for page in response:
            row.append(page["compressedStructuredContent"])

        nertoparse.append({"compressedStructuredContent": row})


        nerExtracted = extractNer(nertoparse)

        if mongoid and ObjectId.is_valid(mongoid):
            ret = db.emailStored.update_one({
                "_id" : ObjectId(mongoid)
            }, {
                "$push": {
                    "pipeline": {
                        "stage" : 4,
                        "name": "ner",
                        "start_time" : time.time(),
                        # "debug" : json.loads(json.dumps(nerExtracted)),
                        "timeTaken": time.time() - timer
                    }
                }
            })
            timer = time.time()

        logger.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ ner time taken %s ", time.time() - timer)
        # fullResponse["nerExtracted"] = nerExtracted

        row = {}
        row["file"] = filename
        row["nerparsed"] = nerExtracted
        row["compressedStructuredContent"] = {}
        for pageIdx, page in enumerate(response):
            row["compressedStructuredContent"][str(
                pageIdx + 1)] = page["compressedStructuredContent"]

        combinData = classifyNer([row])[0]

        if "finalEntity" in combinData:
            if "PERSON" in combinData["finalEntity"]:
                person = combinData["finalEntity"]["PERSON"]["obj"]

                if len(person) > 0:
                    gender  =  getGender(person, account_name, account_config)
                    combinData["finalEntity"]["gender"] = gender
                

        if mongoid and ObjectId.is_valid(mongoid):
            ret = db.emailStored.update_one({
                "_id" : ObjectId(mongoid)
            }, {
                "$push": {
                    "pipeline": {
                        "stage" : 5,
                        "name": "classify",
                        "start_time" : time.time(),
                        # "debug" : json.loads(json.dumps(combinData)),
                        "timeTaken": time.time() - timer
                    }
                }
            })
            timer = time.time()

        newCompressedStructuredContent = {}
        GOOGLE_BUCKET_URL = get_cloud_url(account_name, account_config)

        for pageno in combinData["compressedStructuredContent"].keys():
            pagerows = combinData["compressedStructuredContent"][pageno]
            newCompressedStructuredContent[pageno] = []
            for row in pagerows:
                if "classify" in row or True: #show all for now
                    # classify = row["classify"]
                    # if "append" in row:
                    #     del row["append"]
                    if "finalClaimedIdx" in row:
                        del row["finalClaimedIdx"]
                    if "isboxfound" in row:
                        del row["isboxfound"]
                    if "lineIdx" in row:
                        del row["lineIdx"]
                    if "matchedRow" in row:
                        if "bbox" in row["matchedRow"]:
                            del row["matchedRow"]["bbox"]
                        if "imagesize" in row["matchedRow"]:
                            del row["matchedRow"]["imagesize"]
                        if "matchRatio" in row["matchedRow"]:
                            del row["matchedRow"]["matchRatio"]

                        row["matchedRow"]["bucketurl"] = row["matchedRow"]["filename"].replace(
                            basePath + "/", GOOGLE_BUCKET_URL)

                    if "append" in row:
                        newAppend = []
                        for r in row["append"]:
                            if "row" in r:
                                if "finalClaimedIdx" in r["row"]:
                                    del r["row"]["finalClaimedIdx"]
                                if "isboxfound" in r["row"]:
                                    del r["row"]["isboxfound"]
                                if "lineIdx" in r["row"]:
                                    del r["row"]["lineIdx"]
                                if "matchedRow" in r["row"]:
                                    if "bbox" in r["row"]["matchedRow"]:
                                        del r["row"]["matchedRow"]["bbox"]
                                    if "idx" in r["row"]["matchedRow"]:
                                        del r["row"]["matchedRow"]["idx"]
                                    if "isClaimed" in r["row"]["matchedRow"]:
                                        del r["row"]["matchedRow"]["isClaimed"]
                                    if "imagesize" in r["row"]["matchedRow"]:
                                        del r["row"]["matchedRow"]["imagesize"]
                                    if "matchRatio" in r["row"]["matchedRow"]:
                                        del r["row"]["matchedRow"]["matchRatio"]

                                if "matchedRow" in r["row"]:
                                    r["row"]["matchedRow"]["bucketurl"] = r["row"]["matchedRow"]["filename"].replace(
                                        basePath + "/", GOOGLE_BUCKET_URL)

                            newAppend.append(r)

                        row["append"] = newAppend

                    newCompressedStructuredContent[pageno].append(row)

        combinData["newCompressedStructuredContent"] = newCompressedStructuredContent

        logger.info("full resume parsing completed %s", filename)
        ret = {
            "newCompressedStructuredContent": newCompressedStructuredContent,
            "finalEntity": combinData["finalEntity"],
            "timeTaken": time.time() - init_timer,
            "parsing_type" : parsing_type
        }

        if mongoid:
            t = Thread(target=addToSearch, args=(mongoid,finalLines,ret, account_name, account_config))
            t.start()

        ret["debug"] = {
            # "extractEntity": combinData["extractEntity"],
            # "compressedStructuredContent": combinData["compressedStructuredContent"]
            "nerExtracted" : nerExtracted
        }
        cvdir = ''.join(e for e in filename if e.isalnum())
        shutil.rmtree(BASE_PATH + "/../cvreconstruction/" + cvdir , ignore_errors = True) 
        logger.info("processing completed, final filename %s", filename)
        os.remove(BASE_PATH + "/../cvreconstruction/" + filename) 
        return ret

    except PDFTextExtractionNotAllowed as e:
    # except KeyError as e:
        logger.info("error %s", str(e))
        print(traceback.format_exc())
        return {
            "error": str(e)
        }


def addToSearch(mongoid, finalLines, ret, account_name, account_config):
    sendBlockingMessage({
        "id": mongoid,
        "lines" : finalLines,
        "extra_data" : ret,
        "action" : "addDoc",
        "account_name" : account_name,
        "account_config" : account_config
    })

def getGender(name, account_name, account_config):
    return getGenderMessage({
        "name" : name,
        "account_name" : account_name,
        "account_config" : account_config
    })