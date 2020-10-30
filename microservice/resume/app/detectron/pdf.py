from pdf2image import convert_from_path
from pathlib import Path
import os
# from pdfminer.high_level import extract_text

import fitz
def covertPDFToImage(cv, output_dir, cvfilename, logger):

    logger.debug("creating output dir %s", output_dir)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    doc = fitz.open(cv)  # open document
    pages = doc.pageCount
    if pages >= 20:
        raise Exception("too many pages not a cv " + str(pages))

    for i, page in enumerate(doc):  # iterate through the pages
        pix = page.getPixmap(alpha = False)  # render page to an image
        subpagecvfilename = os.path.join(
            "", output_dir, "page" + str(i) + '.png')
        logger.debug("saving cv images to %s", subpagecvfilename)

        pix.writePNG(subpagecvfilename)  # store image as a PNG
        if i > 5:
            break

    return
    # this is giving poppler error randomly. so using another library for testing 
    pages = 1
    try:
        pages = convert_from_path(cv)
    except expression as identifier:
        pass

    if len(pages) >= 20:
        raise Exception("too many pages not a cv " + str(len(pages)))


    

    
    
    # cvnonum = ''.join(e for e in cvfilename if e.isalnum())
    logger.debug("len of pages %s", len(pages))
    for i, page in enumerate(pages):
        # logger.critical(cv)
        subpagecvfilename = os.path.join(
            "", output_dir, "page" + str(i) + '.png')
        logger.debug("saving cv images to %s", subpagecvfilename)
        page.save(subpagecvfilename, 'PNG')

        if i > 5:
            break
            


def extractTextFromPDF(cv, cvpage):
    content = extract_text(cv, page_numbers=[cvpage-1], maxpages=1)
    return content
