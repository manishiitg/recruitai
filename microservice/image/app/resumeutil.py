from app.image.start import processAPI
from app.config import BASE_PATH
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

from app.account import initDB, get_cloud_url, get_cloud_bucket

def deleteDirContents(folder):
    if not os.path.exists(folder):
        return 

    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logger.critical('Failed to delete %s. Reason: %s' , file_path, e)

def killlibreoffice():
    for proc in psutil.process_iter():
        # check whether the process name matches
        if "soffice" in proc.name():
            proc.kill()

def fullResumeParsing(filename, mongoid=None, skills = None, account_name = "", account_config = {}):
    
    killlibreoffice()
    timer = time.time()

    dest = BASE_PATH + "/../temp"
    deleteDirContents(dest)

    deleteDirContents(BASE_PATH + "/../cvreconstruction")
    # this cannot be done because resumemq needs files from cvreconstruction

    RESUME_UPLOAD_BUCKET = get_cloud_bucket(account_name, account_config)

    bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
    blob = bucket.blob(account_name + "/" + filename)

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

    # file_found = False
    
    # blobs=list(bucket.list_blobs(prefix=account_name))
    # for blob in blobs:
    #     if blob.name == account_name + "/" + filename:
    #         # blob = bucket.blob(filename) # from nodejs we uploading inside a folder called account_name
    #         file_found = True
    #         Path(dest).mkdir(parents=True, exist_ok=True)
    #         filename, file_extension = os.path.splitext(filename)

    #         cvfilename = ''.join(
    #             e for e in filename if e.isalnum()) + file_extension
    #         cvdir = ''.join(e for e in cvfilename if e.isalnum())
    #         try:
    #             blob.download_to_filename(os.path.join(dest, cvfilename))
    #         except  Exception as e:
    #             logger.critical(str(e))
    #             traceback.print_exc(file=sys.stdout)
    #             return {"error" : str(e)}

    #         break

    # if not file_found:
    #     return {"error" : "file not found"}


    org_cv_filename = cvfilename
    filename = cvfilename

    logger.critical("final file name %s", filename)

    if ".pdf" not in filename:
        inputFile = os.path.join(dest, filename)
        if len(file_extension.strip()) > 0:
            filename = filename.replace(file_extension, ".pdf")
        else:
            filename = filename + ".pdf"

        # libreoffice --headless --convert-to pdf /content/finalpdf/*.doc --outdir /content/finalpdf/

        try:
            logger.critical('libreoffice --headless --convert-to pdf ' + inputFile + " --outdir  " + dest)
            x = subprocess.check_call(
                ['libreoffice --headless --convert-to pdf ' + inputFile + " --outdir  " + dest], shell=True, timeout=60)
            logger.critical(x)

            if os.path.exists(os.path.join(dest, filename)):
                # -n to skip existing
                x = subprocess.check_call(['gsutil -m cp -r ' + os.path.join(dest,filename) + " gs://" + RESUME_UPLOAD_BUCKET + "/" + account_name], shell=True)
                logger.critical(x)

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
            logger.critical("file converted")
        else:
            logger.critical("unable to convert file to pdf")
            return {
                "error" : "unable to convert file to pdf"
            }

    fullResponse = {}

    cvfilename = ''.join(
        e for e in filename if e.isalnum())
    cvdir = ''.join(e for e in cvfilename if e.isalnum())

    
    finalImages, output_dir2 = processAPI(os.path.join(dest, filename), account_name, account_config)
    if "error" in finalImages:
        return finalImages
    
    GOOGLE_BUCKET_URL = get_cloud_url(account_name, account_config) + account_name + "/"

    for idx, img in enumerate(finalImages):
        finalImages[idx] = img.replace(output_dir2 + "/", GOOGLE_BUCKET_URL + cvdir + "/")
        
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
