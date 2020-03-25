from app.image.start import processAPI
from app.config import RESUME_UPLOAD_BUCKET, BASE_PATH, GOOGLE_BUCKET_URL
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

import traceback
from subprocess import CalledProcessError , TimeoutExpired

import sys

import time
import psutil

from google.api_core.exceptions import NotFound

db = None
def initDB():
    global db
    if db is None:
        client = MongoClient(os.getenv("RECRUIT_BACKEND_DB")) 
        db = client[os.getenv("RECRUIT_BACKEND_DATABASE")]

    return db

def deleteDirContents(folder):
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.info('Failed to delete %s. Reason: %s' , file_path, e)

def killlibreoffice():
    for proc in psutil.process_iter():
        # check whether the process name matches
        if "soffice" in proc.name():
            proc.kill()

def fullResumeParsing(filename, mongoid=None, skills = None):
    
    killlibreoffice()


    timer = time.time()

    

    dest = BASE_PATH + "/../temp"
    deleteDirContents(dest)
    deleteDirContents(BASE_PATH + "/../cvreconstruction")

    bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
    blob = bucket.blob(filename)

    Path(dest).mkdir(parents=True, exist_ok=True)
    filename, file_extension = os.path.splitext(filename)

    cvfilename = ''.join(
        e for e in filename if e.isalnum()) + file_extension
    cvdir = ''.join(e for e in cvfilename if e.isalnum())
    try:
        blob.download_to_filename(os.path.join(dest, cvfilename))
    except  Exception as e:
        logger.critical(str(e))
        traceback.print_exc(file=sys.stdout)
        return {"error" : str(e)}

    org_cv_filename = cvfilename
    filename = cvfilename

    logger.info("final file name %s", filename)

    if ".pdf" not in filename:
        inputFile = os.path.join(dest, filename)
        if len(file_extension.strip()) > 0:
            filename = filename.replace(file_extension, ".pdf")
        else:
            filename = filename + ".pdf"

        # libreoffice --headless --convert-to pdf /content/finalpdf/*.doc --outdir /content/finalpdf/

        try:
            logger.info('libreoffice --headless --convert-to pdf ' + inputFile + " --outdir  " + dest)
            x = subprocess.check_call(
                ['libreoffice --headless --convert-to pdf ' + inputFile + " --outdir  " + dest], shell=True, timeout=60)
            logger.info(x)
        except CalledProcessError as e:
            logger.critical(str(e))
            traceback.print_exc(file=sys.stdout)
            # os.remove(inputFile) 
            return {"error" : str(e)}
        except TimeoutExpired as e:
            logger.critical(str(e))
            traceback.print_exc(file=sys.stdout)
            # os.remove(inputFile) 
            return {"error" : str(e)}

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
    if "error" in finalImages:
        return finalImages

    for idx, img in enumerate(finalImages):
        finalImages[idx] = img.replace(output_dir2 + "/", GOOGLE_BUCKET_URL + cvdir + "/")

    if mongoid and ObjectId.is_valid(mongoid):
        db = initDB()
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
        
    shutil.rmtree(os.path.join(dest, cvdir)) 
    if os.path.exists(os.path.join(dest, org_cv_filename)):
        os.remove(os.path.join(dest, org_cv_filename)) 
    if os.path.exists(os.path.join(dest, filename)):
        os.remove(os.path.join(dest, filename)) 


    return {
        "finalImages" : finalImages, 
        "output_dir2" : output_dir2, 
        "cvdir" : cvdir , 
        "filename": filename
    }
