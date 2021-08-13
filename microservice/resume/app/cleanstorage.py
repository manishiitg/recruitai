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

from app.account import initDB, get_cloud_bucket, get_cloud_url
from app.config import storage_client


def main():
    pass


    # dest = BASE_PATH + "/../c vreconstruction/"
    # RESUME_UPLOAD_BUCKET = "airecruitai.excellencetechnologies.in"
    # account_name = "excellencerecruit"

    # # gsutil ls -d gs://airecruitai.excellencetechnologies.in/excellencerecruit
    # # x = subprocess.check_call(
    # #     ['gsutil ls -d ' + "gs://" + RESUME_UPLOAD_BUCKET + "/" + account_name], shell=True)

    # blobs = storage_client.list_blobs(
    #     "airecruitai.excellencetechnologies.in", prefix="excellencerecruit")

    # idx = 0
    # total_delete = 0
    # for blob in blobs:
    #     idx = idx + 1
    #     if("_" in blob.name and "person" not in blob.name):
    #         print("deleting ", blob.name)
    #         blob.delete()
    #         total_delete += 1
    #         pass
    #     else:
    #         print("not deleting ", blob.name)
    #     # if idx > 10000:
    #     #     break
    
    # print("total delete %s", total_delete)


if __name__ == '__main__':
    main()
