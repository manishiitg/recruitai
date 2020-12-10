from app.picture.start import processAPI as extractPicture
from app.config import BASE_PATH
from app.logging import logger
from app.config import storage_client
from pathlib import Path
import subprocess
import os
import shutil  
import traceback

from threading import Thread

import json

from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

import time
import urllib.request

import sys

from app.account import initDB, get_cloud_bucket, get_cloud_url

def fullResumeParsing(imageUrl, mongoid, filename, account_name, account_config):
    try:
        db = initDB(account_name, account_config)
        candidaterow = db.emailStored.find_one({"_id" : ObjectId(mongoid)})
        if "cvimage" in candidaterow:
            if "picture" in candidaterow["cvimage"]:
                logger.critical("this was already processed. remove this if new ai model comes")
                return{}



        GOOGLE_BUCKET_URL = get_cloud_url(account_name, account_config)
        timer = time.time()
        db = initDB(account_name, account_config)

        fullResponse = {}
        
        cvdir = ''.join(e for e in filename if e.isalnum())
        dest = BASE_PATH + "/../picextract/" + cvdir

        shutil.rmtree(dest , ignore_errors = True) 
        Path(dest).mkdir(parents=True, exist_ok=True)
        

        logger.critical("downloading from url %s", imageUrl)
        finalPic = os.path.join(dest, filename + ".png")
        # urllib.request.urlretrieve(imageUrl, finalPic)

        
        RESUME_UPLOAD_BUCKET = get_cloud_bucket(account_name, account_config)

        bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
        imageUrl = imageUrl.replace(GOOGLE_BUCKET_URL,"")
        logger.critical("image replacement %s with bucket %s", imageUrl, GOOGLE_BUCKET_URL)

        logger.critical("download image %s", imageUrl)
        blob = bucket.blob(imageUrl)

        try:
            blob.download_to_filename(finalPic)
        except  Exception as e:
            logger.critical(str(e))
            traceback.print_exc(file=sys.stdout)
            return {"error" : str(e)}

        

        response, basedir = extractPicture(dest ,cvdir, account_name, account_config)
        


        if response:
            response = response.replace(basedir + "/", "")
            response = GOOGLE_BUCKET_URL + account_name + "/" + cvdir + "/picture/" + response
            logger.critical(response)

            if mongoid and ObjectId.is_valid(mongoid):
                db = initDB(account_name, account_config)
                ret = db.emailStored.update_one({
                    "_id" : ObjectId(mongoid)
                }, {
                    "$set": {
                        "cvimage.picture": response
                    }
                })  


        
        shutil.rmtree(dest , ignore_errors = False) 
        return {}

    except Exception as e:
        logger.critical("error %s", str(e))
        print(traceback.format_exc())
        return {
            "error": str(e)
        }
