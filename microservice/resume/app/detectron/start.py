from app.detectron.pdf import extractTextFromPDF
from app.detectron.logic import chooseBBoxVsSegment, identifyTableData, finalCompressedContent
from app.detectron.ocr import extractOcrTextFromSegments
from app.detectron.predict import savePredictionPartsToFile
from app.detectron.pdf import covertPDFToImage
from app.account import get_cloud_bucket, get_cloud_url
import time
from tqdm import tqdm
import subprocess
from app.config import storage_client
from google.cloud import storage
import glob
from pdfminer.high_level import extract_text
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
import json
from PIL import Image
from pathlib import Path
import shutil
from threading import Thread
from app.detectron.text import get_content_from_resume

import torch

from app.config import BASE_PATH

# from app import mongo

import logging
import os
import pycocotools.mask as mask_util

import random
import cv2
import re
import numpy as np
import detectron2
from detectron2.utils.logger import setup_logger
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor
setup_logger()


# You may need to restart your runtime prior to this, to let your installation take effect
# Some basic setup
# Setup detectron2 logger
logger = setup_logger()

# import some common libraries


def cv2_imshow(im):
    pass


# import some common detectron2 utilities
device = 'cuda' if torch.cuda.is_available() else 'cpu'
logger.critical("device found %s", device)
baseDirectory = BASE_PATH + "/detectron"


predictor = None
cfg = None


def test():
    logger.critical("loading model")
    predictor, cfg = loadTrainedModel()
    logger.critical("model loaded")
    logger.setLevel(logging.INFO)
    logger.critical("device available %s", device)
    files = getFilesToParseForTesting()
    # else:
    #   logger.setLevel(logging.CRITICAL)
    #   files = getFilesToParseFromDB()

    inputDir = baseDirectory + "/../../finalpdf"
    basePath = baseDirectory + "/../../cvreconstruction"
    Path(inputDir).mkdir(parents=True, exist_ok=True)
    Path(basePath).mkdir(parents=True, exist_ok=True)

    compressedStructuredContent, timeAnalysis, predictions, jsonOutputbbox, page_contents = startProcessing(
        files, inputDir, basePath, predictor, cfg)
    return compressedStructuredContent


def processAPI(file, account_name, account_config, maxPage=False, candidate_row=None):

    filestoparse = [{
        "file": file,
        "id": -1
    }]

    inputDir = baseDirectory + "/../../finalpdf"
    basePath = baseDirectory + "/../../cvreconstruction"
    Path(inputDir).mkdir(parents=True, exist_ok=True)
    Path(basePath).mkdir(parents=True, exist_ok=True)
    predictor, cfg = loadTrainedModel()
    compressedStructuredContent, timeAnalysis, predictions, jsonOutputbbox, page_contents = startProcessing(
        filestoparse, inputDir, basePath, predictor, cfg, maxPage, account_name, account_config, candidate_row)
    assert len(compressedStructuredContent) == 1
    logger.critical("page contents sssssss %s", page_contents)
    return compressedStructuredContent[0], basePath, timeAnalysis, predictions, jsonOutputbbox, page_contents


def startProcessing(filestoparse, inputDir, basePath, predictor, cfg, maxPage=False, account_name="", account_config={}, candidate_row=None):
    timeAnalysis = {}

    combinedCompressedContent = {}
    # exist_predictions = None
    # exist_jsonOutputbbox = None

    # if "cvParsedInfo" in candidate_row:
    #   cvParsedInfo = candidate_row["cvParsedInfo"]
    #   if "debug" in cvParsedInfo:
    #     debug = cvParsedInfo["debug"]
    #     if "predictions" in debug:
    #       exist_predictions = debug["predictions"]
    #     if "jsonOutputbbox" in debug:
    #       exist_jsonOutputbbox = debug["jsonOutputbbox"]

    #   # not sure how to use these. need to think
    #   # basically not need to parse resume everytime again and again

    for fileIdx in tqdm(range(len(filestoparse))):

        timeAnalysis[fileIdx] = {}
        start_time = time.time()

        combinedCompressedContent[fileIdx] = []

        logger.info(filestoparse[fileIdx])
        # if filestoparse[fileIdx]["id"] != -1:
        #   mongo.db.cvparsingsample.update_one({"_id" : filestoparse[fileIdx]["id"]}, { "$set" : { "parsed" : True } })

        # copy from source directory to input directory
        cv = shutil.copy(filestoparse[fileIdx]["file"],  inputDir)

        cv = os.path.join(inputDir, os.path.basename(
            filestoparse[fileIdx]["file"]))
        logger.info("file path after copy %s", cv)

        if not os.path.exists(cv):
            logger.info("file doesn't exist %s", cv)

        logger.critical("reading cv %s", cv)

        basecv = os.path.basename(cv)
        filename, file_extension = os.path.splitext(basecv)

        cvfilename = ''.join(
            e for e in filename if e.isalnum()) + file_extension
        # try:
        # copy cv to output directory after renaming it
        logger.info("final path %s", os.path.join(basePath, cvfilename))
        cv = shutil.copy(cv,  os.path.join(basePath, cvfilename))
        # except:
        #   pass

        logger.info("final file name %s", cv)
        output_dir = os.path.join(basePath, ''.join(
            e for e in basecv if e.isalnum()))
        # os.remove()
        shutil.rmtree(output_dir, ignore_errors=True)

        start_time = time.time()
        logger.debug("convert pdf to image starting")
        covertPDFToImage(cv, output_dir, cvfilename, logger)
        print("convert pdf to image")
        timeAnalysis[fileIdx]["image_to_pdf"] = time.time() - start_time

        outputFolder = ""
        files = os.listdir(os.path.join(output_dir))

        timeAnalysis[fileIdx]["basic_stuff"] = time.time() - start_time
        start_time = time.time()

        predictions = []
        cvpages = 0
        for f in files:
            cvpages += 1
            if not os.path.isfile(os.path.join(output_dir, f)):
                continue
            logger.debug("orgfile %s", f)

            foldername = ''.join(e for e in f if e.isalnum())
            Path(os.path.join(output_dir, foldername)).mkdir(
                parents=True, exist_ok=True)
            p = savePredictionPartsToFile(f, output_dir, os.path.join(basePath, output_dir, foldername), predictor, cfg, [
                                          "Text", "Title", "List", "Table", "Figure"], save_viz=True, save_withoutbbox=False)

            timeAnalysis[fileIdx]["savePredictionPartsToFile" +
                                  str(cvpages)] = time.time() - start_time
            start_time = time.time()

            if p is None:
                logger.critical("if not predictions found we are breaking out")
                break

            predictions.append(p)
            logger.debug(p)

            if maxPage and cvpages >= maxPage:
                break

            if cvpages > 5:
                break
            # doing only page 1 for now

        logger.critical("total pages in cv %s", cvpages)

        bboxocroutputs = []
        page_contents = []
        for cvpage in range(1, cvpages + 1):

            logger.info("page no %s", cvpage)

            logger.info("fetching contents from %s", output_dir)
            outputFolder = ""

            jsonOutputbbox, jsonOutput = extractOcrTextFromSegments(
                cvpage, output_dir, outputFolder, increase_dpi_for_small_image=True)
            bboxocroutputs.append(jsonOutputbbox)
            timeAnalysis[fileIdx]["extractOcrTextFromSegments" +
                                  str(cvpages)] = time.time() - start_time
            start_time = time.time()

            ##################################

            logger.info(" normal image len %s", len(jsonOutput))
            logger.info(" bbox image len %s", len(jsonOutputbbox))

            jsonOutput, tableRow = chooseBBoxVsSegment(
                jsonOutput, jsonOutputbbox)
            timeAnalysis[fileIdx]["chooseBBoxVsSegment" +
                                  str(cvpages)] = time.time() - start_time
            start_time = time.time()

            ##################################

            # import subprocess
            # subprocess.check_call(["pdf2txt.py", "-p"+ str(cvpage) , "-o" + cv + ".txt" , cv])
            # with open(cv + ".txt", encoding="ascii" , errors = "ignore") as f:
            #   content = f.read()

            logger.info("reading cv %s page no: %s", cv, cvpage)

            # logger.debug(content)
            # pdfminer.high_level.extract_text(pdf_file, password='', page_numbers=None, maxpages=0, caching=True, codec='utf-8', laparams=None)

            content, timeAnalysis = get_content_from_resume(
                cv, cvpage, timeAnalysis, fileIdx, cvpages)
            start_time = time.time()
            # logger.info("contenttt %s", content)

            page_contents.append(content)

            ################################

            cleanLineData = cleanContent(content, cvpage, jsonOutput)
            timeAnalysis[fileIdx]["cleanContent" +
                                  str(cvpages)] = time.time() - start_time
            start_time = time.time()
            # if not cleanLineData:
            #   continue
            #   pass

            ########################################

            seperateTableLineMatchedIndexes, jsonOutput = identifyTableData(
                cleanLineData, tableRow, jsonOutput)
            timeAnalysis[fileIdx]["identifyTableData" +
                                  str(cvpages)] = time.time() - start_time
            start_time = time.time()

            ########################################

            compressedStructuredContent, newstructuredContent = finalCompressedContent(
                cleanLineData, jsonOutput, seperateTableLineMatchedIndexes, logger, predictions)
            timeAnalysis[fileIdx]["finalCompressedContent" +
                                  str(cvpages)] = time.time() - start_time
            start_time = time.time()

            logger.debug(compressedStructuredContent)
            logger.info("length of compressed content %s",
                        len(compressedStructuredContent))

            # if filestoparse[fileIdx]["id"] != -1:
            #   mongo.db.cvparsingsample.update_one({"_id" : filestoparse[fileIdx]["id"]},
            #   { "$set" : {
            #     str(cvpage) : {
            #       "compressedStructuredContent" : json.dumps(compressedStructuredContent, indent=2 , sort_keys=True),
            #       "jsonOutput" : json.dumps(jsonOutput, indent=2 , sort_keys=True)
            #       }
            #     }
            #   }
            # )
            combinedCompressedContent[fileIdx].append({
                "compressedStructuredContent": compressedStructuredContent,
                "jsonOutput": jsonOutput
            })

        start_time = time.time()
        # t = Thread(target=uploadToGcloud, args=(basePath, basecv) , daemon = True)
        # t.start()
        uploadToGcloud(basePath, basecv, account_name, account_config)
        timeAnalysis[fileIdx]["gsutil" +
                              str(cvpages)] = time.time() - start_time
        start_time = time.time()

    # compressedStructuredContent , timeAnalysis, predictions, jsonOutputbbox, page_contents
    return combinedCompressedContent, timeAnalysis, predictions, bboxocroutputs, page_contents


def deleteOcrFiles(folder):
    import os
    import glob

    print("fileeeeeeeeeeeeeeeeeeeeeeee %s", folder)
    folder = folder + "/**/*.png"
    for f in glob.glob(folder,recursive=True):
        print("path name %s", f)
        if("_" in f and "person" not in f):
            print("deleting %s", f)
            os.remove(f)


def uploadToGcloud(basePath, basecv, account_name, account_config):
    RESUME_UPLOAD_BUCKET = get_cloud_bucket(account_name, account_config)
    #  -n
    deleteOcrFiles(os.path.join(basePath, ''.join(
        e for e in basecv if e.isalnum())))
        
    try:
        x = subprocess.check_call(['gsutil -m cp -r ' + os.path.join(basePath, ''.join(
            e for e in basecv if e.isalnum())) + " gs://" + RESUME_UPLOAD_BUCKET + "/" + account_name], shell=True)
        logger.info(x)
    except Exception as e:
        logger.critical("gcloud upload error %s", e)


def cleanContent(content, cvpage, jsonOutput):

    logger.critical("content %s", content)
    lineData = content.splitlines()

    # (cid:72)

    cleanLineData = []
    for line in lineData:
        # this is giving warning on server
        line = re.sub('\s+', ' ', line).strip()

        len_words = 0
        for word in list(filter(None, line.split(' '))):
            if len(word) > len_words:
                len_words = len(word)

        if len_words == 1 and len(list(filter(None, line.split(' ')))) > 2:
            # print("some issue with line %s", line)
            line = "".join(line.split(" "))
            # print("new line %s", line)

        # line = ' '.join(line.split())
        if len(line) > 0:
            words = line.split(" ")
            newwords = []
            for word in words:
                if word.find("(cid:") >= 0 and word.find(")") >= 0:
                    pass
                else:
                    newwords.append(word)

            if len(newwords) > 0:
                line = " ".join(newwords)
                cleanLineData.append(line)

    logger.info("length of clean data %s", len(cleanLineData))

    if len(cleanLineData) < 3:
        if cvpage > 1:
            logger.critical(
                "this might be empty pages. we should stop here...")
            # right now not doing this.... its risky and not neeed
        # else:
        logger.critical("very very few lines??? %s", len(cleanLineData))
        logger.critical(
            "this means unable to read from cv properly do to rare issues. in that case need to take data from image itself.")
        cleanLineData = []
        for row in jsonOutput:
            cleanLineData.append(row["correctLine"])
            logger.debug(row["correctLine"])
    else:
        line_without_space = 0
        for line in cleanLineData:
            if " " not in line.strip() and len(line) > 10:  # if more than 10 its not a single word
                line_without_space += 1
            else:
                words = line.split(" ")
                if len(words) == 2:
                    line_without_space += 1

        logger.critical("line without space %s", line_without_space)
        logger.critical("total lines %s", len(cleanLineData))
        if (line_without_space > len(cleanLineData) / 2) and len(cleanLineData) > 10:
            logger.critical(
                "this means unable to read from cv properly do to rare issues. in that case need to take data from image itself.")
            cleanLineData = []
            for row in jsonOutput:
                cleanLineData.append(row["correctLine"])
                logger.debug(row["correctLine"])

        # Tomakeacareerinrepudiatedfieldandwishtojoinanorganizationthatoffersmea

    return cleanLineData


def loadTrainedModel():
    global predictor
    global cfg
    if predictor is None:
        cfg = get_cfg()
        # add project-specific config (e.g., TensorMask) here if you're not running a model in detectron2's core library
        # cfg.merge_from_file(
        #     baseDirectory + "/detectron2/configs/DLA_mask_rcnn_X_101_32x8d_FPN_3x.yaml")
        cfg.merge_from_file(
            baseDirectory + "/detectron2/configs/DLA_mask_rcnn_R_101_FPN_3x.yaml")

        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5  # set threshold for this model
        # Find a model from detectron2's model zoo. You can either use the https://dl.fbaipublicfiles.... url, or use the detectron2:// shorthand
        # cfg.MODEL.WEIGHTS = "resnext101_32x8d/model_final_trimmed.pth"
        # cfg.MODEL.WEIGHTS = os.path.join("pretrained/detectron3_5000/model_final.pth")
        cfg.MODEL.WEIGHTS = os.path.join(
            "/workspace/detectron4_5000_fpn/detectron4_5000_fpn/model_final.pth")

        cfg.MODEL.DEVICE = device
        predictor = DefaultPredictor(cfg)

    return predictor, cfg


def getFilesToParseForTesting():
    bdir = baseDirectory + "/testpdf"
    files = os.listdir(bdir)
    filestoparse = []
    for f in files:
        filestoparse.append({
            "file": os.path.join(bdir, f),
            "id": -1
        })
    return filestoparse

# def getFilesToParseFromDB():
#   ret = mongo.db.cvparsingsample.find({"parsed" : False, "dataset" : 3})
#   filestoparse = []
#   for row in ret:
#     filestoparse.append({
#         "file" : row["file"],
#         "id" : row["_id"]
#     })

#   return filestoparse
