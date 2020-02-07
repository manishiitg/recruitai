from pdf2image import convert_from_path
from pathlib import Path
import os
# from pdfminer.high_level import extract_text


def covertPDFToImage(cv, output_dir, cvfilename, logger):
    pages = convert_from_path(cv)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    # cvnonum = ''.join(e for e in cvfilename if e.isalnum())
    for i, page in enumerate(pages):
        # logger.info(cv)
        subpagecvfilename = os.path.join(
            "", output_dir, "page" + str(i) + '.png')
        logger.debug("saving cv images to %s", subpagecvfilename)
        page.save(subpagecvfilename, 'PNG')


def extractTextFromPDF(cv, cvpage):
    content = extract_text(cv, page_numbers=[cvpage-1], maxpages=1)
    return content
