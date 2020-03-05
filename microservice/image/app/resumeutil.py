from app.image.start import processAPI
from app.config import RESUME_UPLOAD_BUCKET, BASE_PATH, GOOGLE_BUCKET_URL, RECRUIT_BACKEND_DB, RECRUIT_BACKEND_DATABASE
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

from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

import time


client = MongoClient(RECRUIT_BACKEND_DB) 
db = client[RECRUIT_BACKEND_DATABASE]


def fullResumeParsing(filename, mongoid=None, skills = None):

    timer = time.time()

    bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
    blob = bucket.blob(filename)

    dest = BASE_PATH + "/../temp"
    Path(dest).mkdir(parents=True, exist_ok=True)
    filename, file_extension = os.path.splitext(filename)

    cvfilename = ''.join(
        e for e in filename if e.isalnum()) + file_extension
    cvdir = ''.join(e for e in cvfilename if e.isalnum())
    blob.download_to_filename(os.path.join(dest, cvfilename))

    filename = cvfilename

    logger.info("final file name %s", filename)

    if ".pdf" not in filename:
        inputFile = os.path.join(dest, filename)
        if len(file_extension.strip()) > 0:
            filename = filename.replace(file_extension, ".pdf")
        else:
            filename = filename + ".pdf"

        # libreoffice --headless --convert-to pdf /content/finalpdf/*.doc --outdir /content/finalpdf/
        logger.info('libreoffice --headless --convert-to pdf ' + inputFile + " --outdir  " + dest)
        x = subprocess.check_call(
            ['libreoffice --headless --convert-to pdf ' + inputFile + " --outdir  " + dest], shell=True)
        logger.info(x)

        if os.path.exists(os.path.join(dest, filename)):
            logger.info("file converted")
        else:
            logger.info("unable to convert file to pdf")
            return {
                "error" : "unable to convert file to pdf"
            }


    fullResponse = {}

    cvfilename = ''.join(
        e for e in filename if e.isalnum())
    cvdir = ''.join(e for e in cvfilename if e.isalnum())

    finalImages, output_dir2 = processAPI(os.path.join(dest, filename))

    for idx, img in enumerate(finalImages):
        finalImages[idx] = img.replace(output_dir2 + "/", GOOGLE_BUCKET_URL + cvdir + "/")

    if mongoid and ObjectId.is_valid(mongoid):
        ret = db.emailStored.update_one({
            "_id" : ObjectId(mongoid)
        }, {
            "$set": {
                "cvimage": {
                        "images": finalImages,
                        "time_taken" : time.time() - timer
                }
            }
        })
        timer = time.time()


    return [finalImages, output_dir2, cvdir]
