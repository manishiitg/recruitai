import cv2
from app.logging import logger
import os
import numpy as np
from app.config import IN_COLAB
from detectron2.data import MetadataCatalog
from detectron2.structures import BoxMode, Boxes
from detectron2.data import MetadataCatalog
from detectron2.utils.visualizer import Visualizer, GenericMask
from pylab import array, plot, show, axis, arange, figure, uint8 


from detectron2 import model_zoo

def fourChannels(img):
    height, width, channels = img.shape
    if channels < 4:
        new_img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        return new_img

    return img

def savePredictionPartsToFile(filename, inputFolder, outputFolder, predictor, cfg, thing_classes=[], save_viz = True, save_withoutbbox = False):
    logger.debug("reading filename %s", os.path.join(inputFolder, filename))

    # Image data
    # load as 1-channel 8bit grayscale
    image = cv2.imread(os.path.join(inputFolder, filename), -1)
    # cv2_imshow(image)
    maxIntensity = 255.0
    # depends on dtype of image data
    x = arange(maxIntensity)

    # Parameters for manipulating image data
    phi = 1
    theta = 1

    # Increase intensity such that
    # dark pixels become much brighter,
    # bright pixels become slightly bright
    im = (maxIntensity/phi)*(image/(maxIntensity/theta))**0.8
    im = array(im, dtype=uint8)
    # cv2_imshow(im)
    # im = cv2.imread(os.path.join(inputFolder, filename))

    # im  = image # disabling intensity

    if im is None:
        logger.critical("unable to read image %s",
                    os.path.join(inputFolder, filename))
        return None

    outputs = predictor(im)

    # look at the outputs. See https://detectron2.readthedocs.io/tutorials/models.html#model-output-format for specification
    # logger.critical(outputs["instances"])

    if len(thing_classes) == 0:
        thing_classes = MetadataCatalog.get(
            cfg.DATASETS.TRAIN[0]).get("thing_classes", None)
    else:
        MetadataCatalog.get(cfg.DATASETS.TRAIN[0]).set(
            thing_classes=thing_classes)

    # logger.critical(outputs["instances"])

    boxes = outputs["instances"].pred_boxes.tensor.cpu().numpy()
    boxeswh = BoxMode.convert(boxes, BoxMode.XYXY_ABS, BoxMode.XYWH_ABS)

    classes = outputs["instances"].pred_classes
    scores = outputs["instances"].scores

    masks = []
    has_mask = outputs["instances"].has("pred_masks")
    if has_mask:
        masks = [GenericMask(x, outputs["instances"].image_size[0], outputs["instances"].image_size[1])
                 for x in outputs["instances"].pred_masks.cpu().numpy()]

    if len(masks) == 0:
        logger.critical("unable to find anything from file %s", filename)

    if save_viz:
      v = Visualizer(
          im[:, :, ::-1], MetadataCatalog.get(cfg.DATASETS.TRAIN[0]), scale=1)
      v = v.draw_instance_predictions(outputs["instances"].to("cpu"))
      vizimag = v.get_image()[:, :, ::-1]
      finalfilename = os.path.join(outputFolder, filename + "_viz_.png")
      cv2.imwrite(finalfilename, vizimag)

    # original image
    # -1 loads as-is so if it will be 3 or 4 channel as the original
    # image = cv2.imread(filename, -1)
    image = im

    # set to 4 channels
    image = fourChannels(image)

    # fill the ROI so it doesn't get wiped out when the mask is applied
    channel_count = image.shape[2]  # i.e. 3 or 4 depending on your image
    ignore_mask_color = (255,)*channel_count

    personClass = 0
    # we can put condition to find only person class

    ret = []

    for idx, mask in enumerate(masks):
        classname = thing_classes[int(classes[idx].cpu())]
        score = scores[idx]
        logger.debug("class name found %s", classname)

        # # mask defaulting to black for 3-channel and transparent for 4-channel
        # # (of course replace corners with yours)

        rois = []
        for pi, poly in enumerate(masks[idx].polygons):
            # polyrois = []
            for i in range(len(poly)):
                if i % 2 == 0 and poly[i+1] is not None:
                    rois.append([int(poly[i]), int(poly[i+1])])

            # rois.append(polyrois)

        # logger.critical(rois)
        bbox = boxeswh[idx]
        
        # apply the mask
        x = int(bbox[0])
        y = int(bbox[1])
        w = int(bbox[2])
        h = int(bbox[3])
        fullname, file_extension = os.path.splitext(filename)
        filenameonlyalnum = ''.join(e for e in filename if e.isalnum())
        if not save_withoutbbox:
            try:
                mask = np.zeros(image.shape, dtype=np.uint8)
                cv2.fillPoly(mask, np.array([rois], dtype=np.int32), ignore_mask_color)
                # from Masterfool: use cv2.fillConvexPoly if you know it's convex

                # apply the mask
                masked_image = cv2.bitwise_and(image, mask)
                

                nimg = masked_image[y:y+h, x:x+w]

                # save the result
                
                finalfilename = os.path.join(outputFolder , filenameonlyalnum + "_" + str(idx) + \
                    "_" + str(classname) + "_" + str(score.item()) + ".png")
                logger.critical("writing image %s", finalfilename)
                cv2.imwrite(finalfilename, nimg)
            except cv2.error as e:
                pass
          

        padding = 10
        paddingX = x - padding
        if paddingX < 0:
            paddingX = x

        paddingY = y - padding
        if paddingY < 0:
            paddingY = y

        heightX = y + h + padding
        widthY = x + w + padding
        imageWidth = image.shape[0]
        imageHeight = image.shape[1]

        if heightX >= imageHeight:
            heightX = y + h

        if widthY >= imageWidth:
            widthY = x + w

        bboximage = image[paddingY:heightX, paddingX: widthY]
        finalfilenamebbox = os.path.join(outputFolder, filenameonlyalnum + "_" + str(idx) +
                                         "_" + str(classname) + "_" + str(score.item()) + "_bbox_" + ".png")

        logger.critical("writing image %s", finalfilenamebbox)
        # cv2_imshow(bboximage)
        cv2.imwrite(finalfilenamebbox, bboximage)

        ret.append({
            "bbox": bbox,
            "filename": finalfilename,
            "finalfilenamebbox": finalfilenamebbox,
            "classname": classname,
            "score": str(score.item()),
            "idx": idx
        })

    return {
        "instances": ret,
        "imagewidth": outputs["instances"].image_size[0],
        "imageheight": outputs["instances"].image_size[0],
        "filename": filename
    }

def cmp(name):
    if "_viz_" in name:
        return -1

    if "_" not in name:
        return -1
    start = name.find("_") + 1
    end = name.find("_", start)
    return int(name[start:end])
