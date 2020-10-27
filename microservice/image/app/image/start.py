from app.logging import logger
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError 
import json
from PIL import Image
from pathlib import Path
import shutil

from app.config import BASE_PATH

# from app import mongo

import logging
import os

import random
import re
import subprocess
import traceback
import sys

from app.account import get_cloud_bucket

# You may need to restart your runtime prior to this, to let your installation take effect
# Some basic setup
# Setup detectron2 logger

# import some common detectron2 utilities

def processAPI(filename, account_name, account_config):
    logger.info("start picture identify on %s", filename)
    f = {"file" : filename}

    actualfilename = os.path.basename(filename)

    namenonum = ''.join(e for e in actualfilename if e.isalnum())

    output_dir = os.path.join(BASE_PATH + "/../temp", namenonum)

    logger.info("output dir %s", output_dir)
    finalImages, output_dir2 = savePDFAsImage(f["file"], output_dir, account_name, account_config)    
    return finalImages, output_dir2


def savePDFAsImage(cv, output_dir , account_name, account_config):
    RESUME_UPLOAD_BUCKET = get_cloud_bucket(account_name, account_config)
    shutil.rmtree(output_dir, ignore_errors=True)
    logger.info("reading pdf %s", cv)
    # get_image_from_magick(cv)
    # process.exit(0)
    try:
        pages = convert_from_path(cv)
    except PDFPageCountError as e:
        logger.critical(str(e))
        traceback.print_exc(file=sys.stdout)
        return {"error" : str(e)} , None
    except ValueError as e:
        logger.critical(str(e))
        traceback.print_exc(file=sys.stdout)
        return {"error" : str(e)} , None

    

    if len(pages) >= 20:
        return {"error" : 'No of pages is too much ' + str(len(pages)) } , None

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    cvdir = os.path.dirname(cv)
    cvfilename = cv.replace(cvdir, "")
    cvfilename = ''.join(
        e for e in cvfilename if e.isalnum())
    
    finalPages = []

    basecv = os.path.basename(cv)
    filename, file_extension = os.path.splitext(basecv)
    cvfilename = ''.join(e for e in filename if e.isalnum())  + file_extension
    basePath = BASE_PATH + "/../cvreconstruction"
    logger.info("final filename  %s" , os.path.join(basePath,cvfilename))
    cv = shutil.copy(cv,  os.path.join(basePath,cvfilename))  
    logger.info("final file name %s" , cv)
    output_dir2 = os.path.join(basePath,''.join(e for e in basecv if e.isalnum()))

    Path(output_dir2).mkdir(parents=True, exist_ok=True)

    for i, page in enumerate(pages):
        logger.info("saving pdf image at %s", os.path.join(output_dir,
                                                           cvfilename + "page" + str(i) + '.png'))
        page.save(os.path.join(output_dir,
                               cvfilename + "page" + str(i) + '.png'), 'PNG')


        subpagecvfilename = os.path.join(
            "", output_dir2, "page" + str(i) + '.png')
        logger.debug("saving cv images to %s", subpagecvfilename)

        shutil.copy(os.path.join(output_dir,
                               cvfilename + "page" + str(i) + '.png'),  subpagecvfilename)  


        finalPages.append(subpagecvfilename)

        if i > 5:
            break
            # max5 pages per cv or it could some wrong document also. ie non cv
    # -n to skip existing
    x = subprocess.check_call(['gsutil -m cp -r ' + os.path.join(output_dir2) + " gs://" + RESUME_UPLOAD_BUCKET + "/" + account_name], shell=True)
    logger.info(x)

    return finalPages, output_dir2

# from wand.image import Image as wi
# def get_image_from_magick(cv):
#     logger.critical("Cv %s", cv)

           

#     # result = subprocess.run(['convert', cv, 'page-%03d.png'], stdout=subprocess.PIPE)

#     # print(result)
#     # return
    
#     pdf = wi(filename=cv, resolution=300)
#     pdfimage = pdf.convert("png")
#     i=1
#     logger.critical(pdfimage)
#     for img in pdfimage.sequence:
#         page = wi(image=img)
#         logger.critical("sss %s", (str(i)+".png"))
#         page.save(filename=str(i)+".png")
#         i +=1