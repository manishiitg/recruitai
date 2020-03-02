from app.logging import logger
from pdf2image import convert_from_path
from detectron2.structures import BoxMode, Boxes
from detectron2.data import MetadataCatalog
from detectron2.utils.visualizer import Visualizer, GenericMask
from detectron2 import model_zoo
import json
from PIL import Image
from pathlib import Path
import shutil
import torch

from app.config import IN_COLAB
from app.config import BASE_PATH, RESUME_UPLOAD_BUCKET

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

predictor = None
cfg = None
device = 'cuda' if torch.cuda.is_available() else 'cpu'

logger.debug(device)


def test():
    logger.info("loading model")
    predictor, cfg = loadTrainedModel()
    logger.info("model loaded")
    logger.setLevel(logging.INFO)
    logger.info("device available %s", device)
    files = getFilesToParseForTesting()

    for fileIdx, f in enumerate(files):
        output_dir = os.path.join(BASE_PATH + "/../temp", ''.join(
            e for e in f["file"] if e.isalnum()))

        logger.info("output dir %s", output_dir)
        savePDFAsImage(f["file"], output_dir)
        imageFile = process(output_dir, predictor, cfg)
        logger.info("pic found %s", imageFile)
        files[fileIdx]["imageFile"] = imageFile

        # if files[fileIdx]["id"] != -1:
        #     mongo.db.cvparsingsample.update_one({"_id": files[fileIdx]["id"]},
        #                                         {
        #         "$set": {
        #             "imageFile": imageFile
        #         }
        #     }
        #     )

    return files


def processAPI(filename):
    logger.info("start picture identify on %s", filename)
    f = {"file" : filename}

    actualfilename = os.path.basename(filename)

    namenonum = ''.join(e for e in actualfilename if e.isalnum())

    output_dir = os.path.join(BASE_PATH + "/../temp", namenonum)

    logger.info("output dir %s", output_dir)
    finalImages, output_dir2 = savePDFAsImage(f["file"], output_dir)
    predictor, cfg = loadTrainedModel()
    imageFile = process(output_dir, predictor, cfg)
    logger.info("pic found %s", imageFile)
    if imageFile:
        x = subprocess.check_call(['gsutil -m cp -r ' + output_dir + " gs://" + RESUME_UPLOAD_BUCKET + "/" + namenonum + "/picture"], shell=True)
        logger.info(x)

    return imageFile , output_dir, finalImages, output_dir2

def loadTrainedModel():
    global predictor
    global cfg
    if not predictor:
        cfg = get_cfg()
        # add project-specific config (e.g., TensorMask) here if you're not running a model in detectron2's core library
        cfg.merge_from_file(model_zoo.get_config_file(
            "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5  # set threshold for this model
        # Find a model from detectron2's model zoo. You can either use the https://dl.fbaipublicfiles.... url, or use the detectron2:// shorthand
        cfg.MODEL.WEIGHTS = "detectron2://COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x/137849600/model_final_f10217.pkl"
        cfg.MODEL.DEVICE = device
        predictor = DefaultPredictor(cfg)
    return predictor, cfg


def getFilesToParseForTesting():
    bdir = BASE_PATH + "/detectron/testpdf"
    files = os.listdir(bdir)
    filestoparse = []
    for f in files:
        filestoparse.append({
            "file": os.path.join(bdir, f),
            "id": -1
        })
    return filestoparse


def getFilesToParseFromDB():
    # ret = mongo.db.cvparsingsample.find({"parsed": False, "dataset": 3})
    # filestoparse = []
    # for row in ret:
    #     filestoparse.append({
    #         "file": row["file"],
    #         "id": row["_id"]
    #     })

    # return filestoparse
    return []


def savePDFAsImage(cv, output_dir):
    shutil.rmtree(output_dir, ignore_errors=True)
    logger.info("reading pdf %s", cv)
    pages = convert_from_path(cv)
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
        # checking for pic only on the first page
        break


    x = subprocess.check_call(['gsutil -m cp -r -n ' + os.path.join(output_dir2) + " gs://" + RESUME_UPLOAD_BUCKET], shell=True)
    logger.info(x)

    return finalPages, output_dir2


def process(output_dir, predictor, cfg):
    files = os.listdir(output_dir)
    file = os.path.join(output_dir, files[0])
    logger.info("reading file %s", file)

    filename = os.path.join(output_dir, file)
    im = cv2.imread(filename)

    outputs = predictor(im)

    # look at the outputs. See https://detectron2.readthedocs.io/tutorials/models.html#model-output-format for specification
    outputs["instances"].pred_classes
    outputs["instances"].pred_boxes

    thing_classes = MetadataCatalog.get(
        cfg.DATASETS.TRAIN[0]).get("thing_classes", None)

    boxes = outputs["instances"].pred_boxes.tensor.numpy()
    boxeswh = BoxMode.convert(boxes, BoxMode.XYXY_ABS, BoxMode.XYWH_ABS)

    classes = outputs["instances"].pred_classes
    scores = outputs["instances"].scores

    masks = []
    has_mask = outputs["instances"].has("pred_masks")
    if has_mask:
        masks = [GenericMask(x, outputs["instances"].image_size[0], outputs["instances"].image_size[1])
                 for x in outputs["instances"].pred_masks.cpu().numpy()]

    # original image
    # -1 loads as-is so if it will be 3 or 4 channel as the original
    # image = cv2.imread(filename, -1)
    image = im

    # set to 4 channels
    image = fourChannels(image)

    # fill the ROI so it doesn't get wiped out when the mask is applied
    channel_count = image.shape[2]  # i.e. 3 or 4 depending on your image
    ignore_mask_color = (255,)*channel_count

    finalPicImage = False

    for idx, mask in enumerate(masks):
        classname = thing_classes[int(classes[idx].cpu())]
        score = scores[idx]
        logger.info("class name found %s", classname)

        if classname == "person":

            # # mask defaulting to black for 3-channel and transparent for 4-channel
            # # (of course replace corners with yours)

            rois = []
            for pi, poly in enumerate(masks[idx].polygons):
                # polyrois = []
                for i in range(len(poly)):
                    if i % 2 == 0 and poly[i+1] is not None:
                        rois.append([int(poly[i]), int(poly[i+1])])

                # rois.append(polyrois)

            # logger.info(rois)

            mask = np.zeros(image.shape, dtype=np.uint8)
            cv2.fillPoly(mask, np.array(
                [rois], dtype=np.int32), ignore_mask_color)
            # from Masterfool: use cv2.fillConvexPoly if you know it's convex

            # apply the mask
            masked_image = cv2.bitwise_and(image, mask)
            bbox = boxeswh[idx]

            x = int(bbox[0])
            y = int(bbox[1])
            w = int(bbox[2])
            h = int(bbox[3])
            nimg = masked_image[y:y+h, x:x+w]

            # save the result
            fullname, file_extension = os.path.splitext(file)
            finalfilename = os.path.join("", fullname + "_" + str(idx) +
                                         "_" + str(classname) + "_" + str(score.item()) + ".png")
            logger.info("writing image %s", finalfilename)
            cv2.imwrite(finalfilename, nimg)
            finalPicImage = finalfilename

    return finalPicImage


def fourChannels(img):
    height, width, channels = img.shape
    if channels < 4:
        new_img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        return new_img

    return img
