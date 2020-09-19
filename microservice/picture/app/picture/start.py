from app.logging import logger
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

from app.account import get_cloud_bucket

# import some common detectron2 utilities

predictor = None
cfg = None
device = 'cuda' if torch.cuda.is_available() else 'cpu'

logger.critical("device found %s", device)


def processAPI(output_dir, namenonum, account_name, account_config):
    logger.critical("start picture identify on %s", output_dir)
    
    logger.critical("output dir %s", output_dir)
    # finalImages, output_dir2 = 
    predictor, cfg = loadTrainedModel()
    imageFile = process(output_dir, predictor, cfg)
    logger.critical("pic found %s", imageFile)
    if imageFile:
        RESUME_UPLOAD_BUCKET  = get_cloud_bucket(account_name, account_config)
        x = subprocess.check_call(['gsutil -m cp -r ' + output_dir + " gs://" + RESUME_UPLOAD_BUCKET + "/" + account_name + "/" + namenonum + "/picture"], shell=True)
        logger.critical(x)

    return imageFile , output_dir

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

def process(output_dir, predictor, cfg):
    files = os.listdir(output_dir)
    file = os.path.join(output_dir, files[0])
    logger.critical("reading file %s", file)

    filename = os.path.join(output_dir, file)
    im = cv2.imread(filename)

    outputs = predictor(im)

    # look at the outputs. See https://detectron2.readthedocs.io/tutorials/models.html#model-output-format for specification
    outputs["instances"].pred_classes
    outputs["instances"].pred_boxes

    thing_classes = MetadataCatalog.get(
        cfg.DATASETS.TRAIN[0]).get("thing_classes", None)

    if device == "cuda":
        boxes = outputs["instances"].pred_boxes.tensor.cpu().numpy()
    else:
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
        logger.critical("class name found %s", classname)

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
            logger.critical("writing image %s", finalfilename)
            cv2.imwrite(finalfilename, nimg)
            finalPicImage = finalfilename

    return finalPicImage


def fourChannels(img):
    height, width, channels = img.shape
    if channels < 4:
        new_img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        return new_img

    return img
