import os
from app.config import RESUME_UPLOAD_BUCKET, BASE_PATH
import subprocess
from app.logging import logger
from app import mongo
from app.resumeutil import fullResumeParsing
import time
from pathlib import Path
import json

def process_resumes():
    batchDir = BASE_PATH + "/../batchresumeprocessing"
    logger.info('running batch resume processing... %s' , batchDir)
    Path(batchDir).mkdir(parents=True, exist_ok=True)
    files = os.listdir(batchDir)
    if len(files) > 0:
        filename = files[0]
        batchfile = os.path.join(batchDir, filename)


        x = subprocess.check_call(['gsutil -m cp -n ' + batchfile + " gs://" + RESUME_UPLOAD_BUCKET], shell=True)
        logger.info(x)

        os.remove(batchfile)

        start_time = time.time()
        ret = fullResumeParsing(filename, True)
        end_time = time.time()

        mongo.db.cvparsingsample.insert_one({
            "file" : filename,
            "isBatch" : True,
            "fullParse" :  json.dumps(ret),
            "timeTaken" : end_time - start_time
        })

    else:
        logger.info("no files in batch")