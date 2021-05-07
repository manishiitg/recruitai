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

from app.publishsearch import sendMessage
from app.publishgender import sendBlockingMessage as getGenderMessage
from app.publishsummary import sendMessage as sendSummary

from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

import time

from pdfminer.pdfpage import PDFTextExtractionNotAllowed

from app.fast.start import process as processFast

from app.statspublisher import sendMessage as updateStats

import sys
import copy

from app.account import initDB, get_cloud_bucket, get_cloud_url

def fullResumeParsing(filename, mongoid=None, message = None , priority = 0, account_name = "", account_config = {}, candidate_row = None):
    try:


        init_timer = time.time()
        timer = time.time()

        dest = BASE_PATH + "/../cvreconstruction/"
        RESUME_UPLOAD_BUCKET = get_cloud_bucket(account_name, account_config)

        bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
        blob = bucket.blob(account_name + "/" + filename)
        Path(dest).mkdir(parents=True, exist_ok=True)
        try:
            filename = filename.replace("'","") #one case we have a file with ' in it which cause issue
            blob.download_to_filename(os.path.join(dest, filename))
            logger.critical("file downloaded at %s", os.path.join(dest, filename))


            logger.critical("file exists %s", os.path.isfile(os.path.join(dest, filename)))
            if not os.path.isfile(os.path.join(dest, filename)):
                logger.critical("file not downloaded" + account_name + "/" + filename)
                return {"error" : "file not downloaded" + account_name + "/" + filename}

        except  Exception as e:
            logger.critical("error exception %s",str(e))
            traceback.print_exc(file=sys.stdout)
            return {"error" : str(e)}

        db = initDB(account_name, account_config)
        
       
        fullResponse = {}
        dest = BASE_PATH + "/../cvreconstruction"
            
        predictions = {}
        jsonOutputbbox = {}
        page_contents = {}


        timer = time.time()
        parsing_type = "full"
        if priority > 7 :
            parsing_type = "full"
        else:
            parsing_type = "fast"


        # parsing_type = "full" # temp for testing full always for now 
        # removing this now. old email need to be parsed fast else it takes lot of time 

        timeAnalysis = {}

        if message and "parsing_type" in message:
            parsing_type = message["parsing_type"]

        if parsing_type == "full":
            try:
                response, basePath, timeAnalysis, predictions, jsonOutputbbox, page_contents = processAPI(os.path.join(dest, filename), account_name, account_config)
            except ValueError as e: # for teating removed exception
                logger.critical("error %s", e)
                return {
                    "error": "type2" + str(e) + json.dumps(timeAnalysis, default=str)
                }

            logger.critical("========================================== time analysis ==========================================")
            for fileIdx in timeAnalysis:
                logger.critical("file idx %s" , fileIdx)
                for work in timeAnalysis[fileIdx]:
                    logger.critical("================   work %s time taken %s ", work, timeAnalysis[fileIdx][work])

            logger.critical("total time taken %s", (time.time() - timer))

            logger.critical("========================================== time analysis ==========================================")
        else:
            response , page_contents = processFast(os.path.join(dest, filename))
            timeAnalysis = {}
    

        full_time_analysis = {
            "resume_construction" : {
                "time" : timeAnalysis,
                "time_taken" : time.time() - timer,
                "start_time" : time.time(),    
            }
        }

        timer = time.time()
        
        compressedStructuredContent = []
        finalLines = []
        for page in response:
            compressedStructuredContent.append(copy.deepcopy(page["compressedStructuredContent"]))
            for pagerow in page["compressedStructuredContent"]:
                logger.info(pagerow)
                finalLines.append(pagerow["line"])

        # print(json.dumps(compressedStructuredContent, indent=1))
        if mongoid:
            # addToSearch(mongoid,finalLines,{}, account_name, account_config)
            
            full_time_analysis["searchIdx"] = {
                "time_taken" : time.time() - timer,
                "start_time" : time.time()
            }

        
            timer = time.time()

            # doing this with datasync now 
            pass

        # fullResponse["compressedContent"] = {"response" : response, "basePath" : basePath}

        nertoparse = []
        row = []
        
        for page in response:
            row.append(page["compressedStructuredContent"])
            

        nertoparse.append({"compressedStructuredContent": row})

        

        nerExtracted = extractNer(copy.deepcopy(nertoparse))

        full_time_analysis["ner"] = {
                "time_taken" : time.time() - timer,
                "start_time" : time.time()
            }
        
        timer = time.time()

        logger.critical("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ ner time taken %s ", time.time() - timer)
        # fullResponse["nerExtracted"] = nerExtracted

        row = {}
        row["file"] = filename
        row["nerparsed"] = nerExtracted
        row["compressedStructuredContent"] = {}
        for pageIdx, page in enumerate(response):
            row["compressedStructuredContent"][str(
                pageIdx + 1)] = page["compressedStructuredContent"]


        combinData = classifyNer([row])[0]

        print("========================================")

        

        if "finalEntity" in combinData:
            if "PERSON" in combinData["finalEntity"]:
                person = combinData["finalEntity"]["PERSON"]["obj"]

                if len(person) > 0:
                    gender  =  getGender(person, account_name, account_config)
                    combinData["finalEntity"]["gender"] = gender
                

        full_time_analysis["classify"] = {
            "time_taken" : time.time() - timer,
            "start_time" : time.time()
        }
        timer = time.time()

        newCompressedStructuredContent = {}
        GOOGLE_BUCKET_URL = get_cloud_url(account_name, account_config) + account_name + "/"

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
            "parsing_type" : parsing_type,
            "page_contents" : page_contents
        }

        # if mongoid:
        #     t = Thread(target=addToSearch, args=(mongoid,finalLines,ret, account_name, account_config))
        #     t.start()
        # this is not needed anymore. as we are caching ai data in redis. so no need to store that in search index


        updateStats({
            "action" : "resume_time_analysis",
            "resume_unique_key" : message["filename"],
            "mongoid" : message["mongoid"],
            "timeAnalysis" : full_time_analysis,
            "account_name" : account_name,
            "account_config" : account_config,
            "parsing_type" : parsing_type
        }) 

        # ret["debug"] = {
        #     "extractEntity": combinData["extractEntity"],
        #     "compressedStructuredContent": compressedStructuredContent,
        #     "nerExtracted" : nerExtracted,
        #     "predictions" : json.loads(json.dumps(predictions, default=str)),
        #     "jsonOutputbbox" : json.loads(json.dumps(jsonOutputbbox, default=str)),
        #     "page_contents" : page_contents
        # }

        # print(combinData["compressedStructuredContent"])
        # process.exit(0)

        cvdir = ''.join(e for e in filename if e.isalnum())
        shutil.rmtree(BASE_PATH + "/../cvreconstruction/" + cvdir , ignore_errors = True) 
        logger.critical("processing completed, final filename %s", filename)
        os.remove(BASE_PATH + "/../cvreconstruction/" + filename) 
        return ret

    except PDFTextExtractionNotAllowed as e:
    # except KeyError as e:
        logger.critical("error %s", str(e))
        print(traceback.format_exc())
        return {
            "error": str(e)
        }


def addToSearch(mongoid, finalLines, ret, account_name, account_config):
    sendMessage({
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