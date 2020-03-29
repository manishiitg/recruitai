from app.picture.start import processAPI as extractPicture
from app.config import RESUME_UPLOAD_BUCKET, BASE_PATH, GOOGLE_BUCKET_URL
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

db = None
def initDB():
    global db
    if db is None:
        client = MongoClient(os.getenv("RECRUIT_BACKEND_DB")) 
        db = client[os.getenv("RECRUIT_BACKEND_DATABASE")]

    return db

def fullResumeParsing(imageUrl, mongoid, filename):
    try:

        timer = time.time()
        db = initDB()

        fullResponse = {}
        
        cvdir = ''.join(e for e in filename if e.isalnum())
        dest = BASE_PATH + "/../picextract/" + cvdir

        shutil.rmtree(dest , ignore_errors = True) 
        Path(dest).mkdir(parents=True, exist_ok=True)
        

        logger.info("downloading from url %s", imageUrl)
        finalPic = os.path.join(dest, filename + ".png")
        # urllib.request.urlretrieve(imageUrl, finalPic)

        bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
        imageUrl = imageUrl.replace(GOOGLE_BUCKET_URL,"")

        blob = bucket.blob(imageUrl.replace("https://" + GOOGLE_BUCKET_URL + "/",""))

        try:
            blob.download_to_filename(finalPic)
        except  Exception as e:
            logger.critical(str(e))
            traceback.print_exc(file=sys.stdout)
            return {"error" : str(e)}


        # pic is not being shown anywhere on frontend and 90% cv's dont have it
        # i think it should be trained with document layour analysic
        # or i can use a smaller detectron2 model for this.
        # for now just disableing it 
        

        response, basedir = extractPicture(dest ,cvdir)
        # , finalImages, output_dir2
        response = response.replace(basedir + "/", "")
        response = GOOGLE_BUCKET_URL + cvdir + "/picture/" + response
        logger.info(response)


        if response:

            if mongoid and ObjectId.is_valid(mongoid):
                db = initDB()
                ret = db.emailStored.update_one({
                    "_id" : ObjectId(mongoid)
                }, {
                    "$set": {
                        "cvimage.picture": response
                    }
                })
            


        
        shutil.rmtree(dest , ignore_errors = False) 
        return ret

    except Exception as e:
        logger.info("error %s", str(e))
        print(traceback.format_exc())
        return {
            "error": str(e)
        }
