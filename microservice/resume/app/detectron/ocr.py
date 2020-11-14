import cv2
from app.logging import logger
from PIL import Image
import tempfile
import os
import numpy as np
from tesserocr import PyTessBaseAPI, PSM, OEM
from app.config import IN_COLAB

# import cv2
# print(cv2.__version__)
# process.exit()


IMAGE_SIZE = 400

if IN_COLAB:
    from google.colab.patches import cv2_imshow
else:
    def cv2_imshow(im):
        pass


def cmp(name):
  if "_viz_" in name:
    return -1 

  if "_" not in name:
    return -1
  start = name.find("_") + 1
  end = name.find("_" , start)
  return int( name[start:end] )

def foldercmp(name):
    start = name.find("page") + 4
    return int(name[start:start + 1])



def get_size_of_scaled_image(im):
    # global size
    # if size is None:
    length_x, width_y = im.size
    factor = max(1, int(IMAGE_SIZE / length_x))
    size = factor * length_x, factor * width_y
    return size


def process_image_for_ocr(file_path, withDPI=False):
    logger.info('Processing image for text Extraction')
    if withDPI:
        file_path = set_image_dpi(file_path)

    im_new = remove_noise_and_smooth(file_path)
    return im_new


def set_image_dpi(file_path):
    im = Image.open(file_path)
    # size = (IMAGE_SIZE, IMAGE_SIZE)
    size = get_size_of_scaled_image(im)
    im_resized = im.resize(size, Image.ANTIALIAS)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    temp_filename = temp_file.name
    im_resized.save(temp_filename, dpi=(300, 300))  # best for OCR
    return temp_filename


BINARY_THREHOLD = 180
# https://github.com/yardstick17/image_text_reader/blob/master/image_preprocessing/remove_noise.py


def image_smoothening(img):
    ret1, th1 = cv2.threshold(img, BINARY_THREHOLD, 255, cv2.THRESH_BINARY)
    ret2, th2 = cv2.threshold(th1, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    blur = cv2.GaussianBlur(th2, (1, 1), 0)
    ret3, th3 = cv2.threshold(
        blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th3


def remove_noise_and_smooth(file_name):
    logger.debug('Removing noise and smoothening image')
    img = cv2.imread(file_name, -1)

    # make mask of where the transparent bits are
    trans_mask = img[:, :, 3] == 0

    # replace areas of transparency with white and not transparent
    img[trans_mask] = [255, 255, 255, 255]

    # new image without alpha channel...
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    temp_filename = temp_file.name
    cv2.imwrite(temp_filename, img)
    img = cv2.imread(temp_filename, 0)

    filtered = cv2.adaptiveThreshold(img.astype(
        np.uint8), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 3)

    kernel = np.ones((1, 1), np.uint8)
    opening = cv2.morphologyEx(filtered, cv2.MORPH_OPEN, kernel)
    closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
    img = image_smoothening(img)
    or_image = cv2.bitwise_or(img, closing)
    return or_image


def removeBordersFromTable(filename):
    image = cv2.imread(filename)
    image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    result = image.copy()
    # Remove horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    remove_horizontal = cv2.morphologyEx(
        thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    cnts = cv2.findContours(
        remove_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        cv2.drawContours(result, [c], -1, (255, 255, 255), 5)

    # Remove vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    remove_vertical = cv2.morphologyEx(
        thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    cnts = cv2.findContours(
        remove_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        cv2.drawContours(result, [c], -1, (255, 255, 255), 5)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    temp_filename = temp_file.name
    cv2.imwrite(temp_filename, result)
    img = cv2.imread(temp_filename, 0)

    filtered = cv2.adaptiveThreshold(img.astype(
        np.uint8), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 3)

    kernel = np.ones((1, 1), np.uint8)
    opening = cv2.morphologyEx(filtered, cv2.MORPH_OPEN, kernel)
    closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
    img = image_smoothening(img)
    or_image = cv2.bitwise_or(img, closing)

    return or_image


def extractOcrTextFromSegments(cvpage, output_dir , outputFolder, increase_dpi_for_small_image = True):
    folders = []

    for file in os.listdir(output_dir):

        if os.path.isfile(os.path.join(output_dir, file)):
            continue

        folders.append(file)

    folders.sort(key=foldercmp)

    logger.debug("folders %s", folders)

    size = None
    jsonOutput = []
    jsonOutputbbox = []

    for fileIdx, file in enumerate(folders):

        if fileIdx != cvpage - 1:
            continue

        logger.debug("ocr folder %s", os.path.join(output_dir, file))
        # files = glob(orgfile + '*')
        files = os.listdir(os.path.join(output_dir, file))
        files.sort(key=cmp)

        logger.debug(files)

        for filename in files:

            if "_viz_" in filename or "_ocr" in filename:
                continue

            if "_" not in filename:
                continue

            if "_Figure_" in filename:
                logger.debug("we ignore figures")
                continue

            # if "_Table_" not in filename:
            #   continue

            filename = os.path.join(output_dir, file, filename)

            fullname, file_extension = os.path.splitext(filename)

            # we have two versions here bbox version and segment roi version

            if "_ocr" in fullname:
                fullname = fullname.replace("_ocr", "")
            finalfilename = outputFolder + fullname + "_ocr" + file_extension
            # logger.debug("writing image", finalfilename)

            psmMode = PSM.SINGLE_BLOCK

            if "_Table_" in filename:
                logger.debug("is table changing psm model")
                psmMode = PSM.SPARSE_TEXT

                image = removeBordersFromTable(filename)
            else:
                image = process_image_for_ocr(filename)

            # if logging.getLogger().isEnabledFor(logging.DEBUG):
            #     cv2_imshow(image)

            cv2.imwrite(finalfilename, image)

            with PyTessBaseAPI() as api:
                api.SetImageFile(finalfilename)

                text = api.GetUTF8Text()
                confidance = api.AllWordConfidences()
                logger.debug({"text": text})
                logger.debug(confidance)

                tsv = api.GetTSVText(1)
                correctWords = []
                for tsvline in tsv.splitlines():
                    word = tsvline.split("\t")[-1]
                    conf = tsvline.split("\t")[-2]

                    if int(conf) > 85:
                        word = word.replace("\n", " ").strip()
                        if len(word) > 0:
                            correctWords.append(word)

                if len(confidance) <= 3 and increase_dpi_for_small_image:
                    # this can be very short word. we should increase dpi for this and check
                    image_withdpi = process_image_for_ocr(filename, True)
                    fullname_withdpi, file_extension_withdpi = os.path.splitext(
                        filename)

                    if "_ocr" in fullname_withdpi:
                        fullname_withdpi = fullname_withdpi.replace("_ocr", "")

                    if "_ocr" in fullname_withdpi:
                        fullname_withdpi = fullname_withdpi.replace(
                            "_withdpi", "")

                    finalfilename_withdpi = outputFolder + fullname_withdpi + \
                        "_ocr" + "_withdpi" + file_extension_withdpi
                    # logger.debug("writing image %s", finalfilename)
                    # cv2_imshow(image_withdpi)
                    cv2.imwrite(finalfilename_withdpi, image_withdpi)

                    with PyTessBaseAPI() as api:
                        api.SetImageFile(finalfilename_withdpi)

                        text_withdpi = api.GetUTF8Text()
                        confidance_withdpi = api.AllWordConfidences()
                        logger.debug({"text_withdpi": text_withdpi})
                        logger.debug(confidance_withdpi)

                        tsv_withdpi = api.GetTSVText(1)
                        correctWords_withdpi = []
                        for tsvline_withdpi in tsv_withdpi.splitlines():
                            word_withdpi = tsvline_withdpi.split("\t")[-1]
                            conf_withdpi = tsvline_withdpi.split("\t")[-2]

                            if int(conf_withdpi) > 70:
                                word_withdpi = word_withdpi.replace(
                                    "\n", " ").strip()
                                if len(word_withdpi) > 0:
                                    correctWords_withdpi.append(word_withdpi)

                    if len(correctWords_withdpi) > len(correctWords):
                        correctWords = correctWords_withdpi
                        finalfilename = finalfilename_withdpi
                        confidance = confidance_withdpi    
                        cv2_imshow(image_withdpi)

                correctLine = " ".join(correctWords)
                logger.debug(correctLine)
                logger.debug(finalfilename)

                if len(text) > 0:
                    if "_bbox_" in finalfilename:
                        jsonOutputbbox.append({
                            "filename": finalfilename,
                            "text": text,
                            "confidance": confidance,
                            "correctLine": correctLine
                        })
                    else:
                        jsonOutput.append({
                            "filename": finalfilename,
                            "text": text,
                            "confidance": confidance,
                            "correctLine": correctLine
                        })
    return jsonOutputbbox, jsonOutput
