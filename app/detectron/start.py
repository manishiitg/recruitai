from PIL import Image
from pathlib import Path
import shutil
import torch

from app.config import IN_COLAB
from app.config import BASE_PATH, RESUME_UPLOAD_BUCKET

from app import mongo

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
import json
from pdfminer.pdfpage import PDFTextExtractionNotAllowed

from pdfminer.high_level import extract_text

import glob
from google.cloud import storage

from app.config import storage_client
import subprocess

# You may need to restart your runtime prior to this, to let your installation take effect
# Some basic setup
# Setup detectron2 logger
logger = setup_logger()

# import some common libraries
if IN_COLAB:
    from google.colab.patches import cv2_imshow
else:
    def cv2_imshow(im):
        pass


if IN_COLAB:
    from tqdm import tqdm_notebook as tqdm
else:
    from tqdm import tqdm


# import some common detectron2 utilities


device = 'cuda' if torch.cuda.is_available() else 'cpu'
baseDirectory = BASE_PATH + "/detectron"

from app.detectron.pdf import covertPDFToImage
from app.detectron.predict import savePredictionPartsToFile
from app.detectron.ocr import extractOcrTextFromSegments
from app.detectron.logic import chooseBBoxVsSegment, identifyTableData, finalCompressedContent
from app.detectron.pdf import extractTextFromPDF

predictor = None
cfg = None

def test():
  logger.info("loading model")
  predictor , cfg = loadTrainedModel()
  logger.info("model loaded")
  logger.setLevel(logging.INFO)
  logger.info("device available %s", device)
  files = getFilesToParseForTesting()
  # else:
  #   logger.setLevel(logging.CRITICAL)
  #   files = getFilesToParseFromDB()

  inputDir = baseDirectory + "/../../finalpdf"
  basePath = baseDirectory + "/../../cvreconstruction"
  Path(inputDir).mkdir(parents=True, exist_ok=True)
  Path(basePath).mkdir(parents=True, exist_ok=True)
  compressedStructuredContent = startProcessing(files , inputDir, basePath, predictor, cfg)
  return compressedStructuredContent




def processAPI(file, maxPage = False):
  filestoparse = [{
        "file" : file,
        "id" : -1
    }]

  inputDir = baseDirectory + "/../../finalpdf"
  basePath = baseDirectory + "/../../cvreconstruction"
  Path(inputDir).mkdir(parents=True, exist_ok=True)
  Path(basePath).mkdir(parents=True, exist_ok=True)
  predictor , cfg = loadTrainedModel()
  compressedStructuredContent = startProcessing(filestoparse, inputDir, basePath , predictor, cfg , maxPage)
  assert len(compressedStructuredContent) == 1

  return compressedStructuredContent[0] , basePath

def startProcessing(filestoparse, inputDir, basePath , predictor, cfg , maxPage = False):
  combinedCompressedContent = {}
  for fileIdx in tqdm(range(len(filestoparse))):
    combinedCompressedContent[fileIdx] = []

    logger.info(filestoparse[fileIdx])
    if filestoparse[fileIdx]["id"] != -1:
      mongo.db.cvparsingsample.update_one({"_id" : filestoparse[fileIdx]["id"]}, { "$set" : { "parsed" : True } })
    
    # copy from source directory to input directory
    cv = shutil.copy(filestoparse[fileIdx]["file"],  inputDir)  

    cv = os.path.join(inputDir , os.path.basename(filestoparse[fileIdx]["file"]))
    logger.info("file path after copy %s", cv)
    
    if not os.path.exists(cv):
      logger.critical("file doesn't exist %s" , cv)

    logger.info("reading cv %s", cv)

    basecv = os.path.basename(cv)
    filename, file_extension = os.path.splitext(basecv)

    

    cvfilename = ''.join(e for e in filename if e.isalnum())  + file_extension
    # try:
    # copy cv to output directory after renaming it
    logger.info("final path %s" , os.path.join(basePath,cvfilename))
    cv = shutil.copy(cv,  os.path.join(basePath,cvfilename))  
    # except:
    #   pass

    logger.info("final file name %s" , cv)
    output_dir = os.path.join(basePath,''.join(e for e in basecv if e.isalnum()))
    shutil.rmtree(output_dir,ignore_errors = True)
    covertPDFToImage(cv, output_dir, cvfilename , logger)


    outputFolder = ""
    files = os.listdir(  os.path.join(output_dir)  )

    predictions = []
    cvpages = 0
    for f in files:
      cvpages += 1
      if not os.path.isfile(os.path.join(output_dir, f)):
        continue
      logger.debug("orgfile %s" , f)

      foldername = ''.join(e for e in f if e.isalnum())
      Path(os.path.join(output_dir, foldername)).mkdir(parents=True, exist_ok=True)
      p = savePredictionPartsToFile(f , output_dir ,os.path.join(output_dir, foldername) , predictor, cfg, ["Text","Title", "List","Table", "Figure"])
      predictions.append(p)
      logger.debug(p)
      if maxPage and cvpages >= maxPage:
        break
      # doing only page 1 for now 

    logger.info("total pages in cv %s" , cvpages)
    for cvpage in range(1, cvpages + 1):
    
      logger.debug("page no %s" , cvpage)

      logger.debug("fetching contents from %s", output_dir)
      outputFolder = ""
      jsonOutputbbox, jsonOutput = extractOcrTextFromSegments(cvpage, output_dir, outputFolder)  

      ##################################

      logger.debug(" normal image len %s", len(jsonOutput))
      logger.debug(" bbox image len %s",len(jsonOutputbbox))

      jsonOutput, tableRow = chooseBBoxVsSegment(jsonOutput, jsonOutputbbox)

      ##################################

      # import subprocess
      # subprocess.check_call(["pdf2txt.py", "-p"+ str(cvpage) , "-o" + cv + ".txt" , cv])
      # with open(cv + ".txt", encoding="ascii" , errors = "ignore") as f:
      #   content = f.read()

      logger.debug("reading cv %s page no: %s" , cv, cvpage)

      
      # logger.debug(content)
      # pdfminer.high_level.extract_text(pdf_file, password='', page_numbers=None, maxpages=0, caching=True, codec='utf-8', laparams=None)
      try:
        content = extract_text(cv, page_numbers=[cvpage-1], maxpages=1)
        # content = textract.process(cv , page_numbers=[cvpage-1], maxpages=1)
        content = str(content)
      except PDFTextExtractionNotAllowed as e:
        logger.critical(e)
        if filestoparse[fileIdx]["id"] != -1:
          mongo.db.cvparsingsample.update_one({"_id" : filestoparse[fileIdx]["id"]}, 
            { 
                "$set" : {
                  "error" : str(e)
                }
            }
          )
        logger.critical("skipping due to error in cv extration %s " , filestoparse[fileIdx]["id"])
        continue

      logger.info(content)

      ################################
      
      cleanLineData = cleanContent(content , cvpage , jsonOutput)
      # if not cleanLineData:
      #   continue
      #   pass

      ########################################

      seperateTableLineMatchedIndexes , jsonOutput =  identifyTableData(cleanLineData, tableRow,jsonOutput)

      ########################################
    
      compressedStructuredContent, newstructuredContent = finalCompressedContent(cleanLineData, jsonOutput , seperateTableLineMatchedIndexes, logger, predictions)

      logger.debug(compressedStructuredContent)
      logger.info("length of compressed content %s" , len(compressedStructuredContent))

      if filestoparse[fileIdx]["id"] != -1:
        mongo.db.cvparsingsample.update_one({"_id" : filestoparse[fileIdx]["id"]}, 
        { "$set" : {
          str(cvpage) : {
            "compressedStructuredContent" : json.dumps(compressedStructuredContent, indent=2 , sort_keys=True),
            "jsonOutput" : json.dumps(jsonOutput, indent=2 , sort_keys=True)
            }
          }
        }
      )
      combinedCompressedContent[fileIdx].append({
        "compressedStructuredContent" : compressedStructuredContent,
        "jsonOutput" : jsonOutput
      })

    x = subprocess.check_call(['gsutil -m cp -r -n ' + os.path.join(basePath,''.join(e for e in basecv if e.isalnum())) + " gs://" + RESUME_UPLOAD_BUCKET], shell=True)
    logger.info(x)

  return combinedCompressedContent


def cleanContent(content , cvpage , jsonOutput):
  

  lineData = content.splitlines()

  # (cid:72)

  cleanLineData = []
  for line in lineData:
    line = re.sub('\s+', ' ', line).strip() # this is giving warning on server
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
      logger.critical("this might be empty pages. we should stop here...")
      # right now not doing this.... its risky and not neeed
    # else:
    logger.critical("very very few lines??? %s", len(cleanLineData))
    logger.debug("this means unable to read from cv properly do to rare issues. in that case need to take data from image itself.")
    cleanLineData = []
    for row in jsonOutput:
      cleanLineData.append(row["correctLine"])
      logger.debug(row["correctLine"])
  
    


  

  return cleanLineData


def loadTrainedModel():
  global predictor
  global cfg
  if predictor is  None:
    cfg = get_cfg()
    # add project-specific config (e.g., TensorMask) here if you're not running a model in detectron2's core library
    cfg.merge_from_file(
        baseDirectory + "/detectron2/configs/DLA_mask_rcnn_X_101_32x8d_FPN_3x.yaml")
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5  # set threshold for this model
    # Find a model from detectron2's model zoo. You can either use the https://dl.fbaipublicfiles.... url, or use the detectron2:// shorthand
    # cfg.MODEL.WEIGHTS = "resnext101_32x8d/model_final_trimmed.pth"
    cfg.MODEL.WEIGHTS = os.path.join("pretrained/detectron3_5000/model_final.pth")
    cfg.MODEL.DEVICE = device
    predictor = DefaultPredictor(cfg)

  return predictor, cfg

def getFilesToParseForTesting():
  bdir = baseDirectory + "/testpdf" 
  files = os.listdir( bdir )
  filestoparse = []
  for f in files:
    filestoparse.append({
        "file" : os.path.join(bdir, f),
        "id" : -1
    })
  return filestoparse

def getFilesToParseFromDB():
  ret = mongo.db.cvparsingsample.find({"parsed" : False, "dataset" : 3})
  filestoparse = []
  for row in ret:
    filestoparse.append({
        "file" : row["file"],
        "id" : row["_id"]
    })

  return filestoparse