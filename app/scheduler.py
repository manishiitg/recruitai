import os
from app.config import RESUME_UPLOAD_BUCKET, BASE_PATH, IS_DEV
import subprocess
from app.logging import logger
from app import mongo
from app.resumeutil import fullResumeParsing
import time
from pathlib import Path
import json
from app.db import init_redis
from app.queue import q 

from redis.exceptions import LockError

def process_resumes():
    batchDir = BASE_PATH + "/../batchresumeprocessing"
    logger.info('running batch resume processing... %s', batchDir)

    # r = init_redis()

    # try:

        # with r.lock("batchoperation", blocking_timeout=5, timeout=60*5):
    Path(batchDir).mkdir(parents=True, exist_ok=True)

    jobprocess = mongo.db.cvparsingsample.find_one({
        "isProcessing" : True
    })
    if jobprocess:
        jobid = jobprocess["jobid"]
        job = q.fetch_job(jobid)
        status = job.get_status()
        # Possible values are queued, started, deferred, finished, and failed
        ret = job.result

        if status == "finished" or status == "failed":
            
                
            mongo.db.cvparsingsample.update_one({
                "_id" : jobprocess["_id"]
            },{
                "isProcessing" : False,
                "isCompleted" : True,
                "fullParse":  json.dumps(ret),
                "status" : status
            })
        else:
            start_time = jobprocess["start_time"]
            now_time = time.time()

            if (now_time - start_time ) > 30 * 60: #30min
                # some issue
                mongo.db.cvparsingsample.update_one({
                    "_id" : jobprocess["_id"]
                },{
                    "isProcessing" : False,
                    "isCompleted" : False,
                    "fullParse":  json.dumps(ret),
                    "status" : status
                })

            else:
                logger.info("waiting for existing batch job to finish... %s" , jobid)
                return
    

    files = os.listdir(batchDir)
    if len(files) > 0:
        filename = files[0]
        batchfile = os.path.join(batchDir, filename)

        mongo.db.cvparsingsample.delete_many({
            "file": filename
        })

        # count = mongo.db.cvparsingsample.count({
        #     "file" : filename
        # })

        # if count > 0:
        #     logger.info("file already exists")
        #     os.remove(batchfile)
        #     return

        x = subprocess.check_call(
            ['gsutil -m cp -n "' + batchfile + '" gs://' + RESUME_UPLOAD_BUCKET], shell=True)
        logger.info(x)

        os.remove(batchfile)

        start_time = time.time()

        # ret = fullResumeParsing(filename)

        job = q.enqueue(fullResumeParsing, filename, result_ttl=86400)  # 1 day

        # end_time = time.time()

        mongo.db.cvparsingsample.insert_one({
            "file": filename,
            "isBatch": True,
            "isProcessing" : True,
            "jobid" : job.id,
            "start_time" : start_time
        })

    else:
        logger.info("no files in batch")
    # except LockError as e:
    #     logger.info("the lock wasn't acquired %s", str(e))
