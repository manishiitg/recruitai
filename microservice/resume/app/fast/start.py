from app.logging import logger

from pdfminer.pdfpage import PDFTextExtractionNotAllowed

from pdfminer.high_level import extract_text
from app.config import BASE_PATH
import os
from pymongo import MongoClient
from bson.objectid import ObjectId
import time
import subprocess
from app.detectron.start import cleanContent
from app.detectron.text import get_content_from_resume

def process(finalPdf):
    content = ""
    page_contents = []
    content, timeAnalysis = get_content_from_resume(finalPdf, -1, {}, -1, -1)
    # try:
    #     content = extract_text(finalPdf)
    #     content = str(content)
    # except PDFTextExtractionNotAllowed as e:
    #     logger.critical(e)
            
    #     logger.critical("skipping due to error in cv extration %s " , finalPdf)
    
    # except Exception as e:
        
    #     logger.critical("general exception in trying nodejs text cv extration %s %s " , str(e) , finalPdf)
    #     x = subprocess.check_output(['pdf-text-extract ' + finalPdf], shell=True, timeout=60)
    #     x = x.decode("utf-8") 
    #     # x = re.sub(' +', ' ', x)
    #     logger.critical(x)
    #     start = "[ '"
    #     end = "' ]"

    #     x = x.replace(start, "")
    #     x = x.replace(end, "")
    #     pages_data_extract = x.split("',")
    #     content = " ".join(pages_data_extract)

    logger.critical("content %s", content)  
    page_contents.append(content)

    # sometimes this gives content like this 
    # Tomakeacareerinrepudiatedfieldandwishtojoinanorganizationthatoffersmea
    # how to handle it??

    lines = convert_for_tagging(content)

    logger.critical("lines %s", lines)

    ret = []

    for line in lines:
        ret.append({ "line" : line})
    

    return [{
            "compressedStructuredContent" : ret
        }
    ], page_contents


def convert_for_tagging(text):
  corpus = []
  entities = []
  multiple_n_count = 0
  word = ""
  text_length = len(text)
  max_n_count = 2
  max_seq_len = 100
  min_seq_length = 5

  text = text.replace("\t"," ") 

  count = 0
  for i in range(text_length):
    char = text[i]
    if char == "\n":
      count += 1
    else:
      count = 0
    
    if count > max_n_count:
      max_n_count = count

  if max_n_count > 3:
    max_n_count = 3

  # basically max_n_count will be between 2-3 depending how may actually are there

  # print(max_n_count," max_n_count ")

  for i in range(text_length):
    char = text[i]

    if char == "\n":
        multiple_n_count += 1

        if len(entities) > max_seq_len:
            corpus.append(entities)
            entities = []

    else:
        multiple_n_count = 0

    if multiple_n_count >= max_n_count:
        if len(entities) > min_seq_length:
            corpus.append(entities)
            entities = []

        continue

    if char == "\n":
        if len(word) > 0:
            entities.append( word  )
        word = ""
        # entities.append( ".  O" )
        entity_type = "O"
    else:
        if char == " ":
            if len(word) > 0:
                entities.append( word  )
            word = ""
        else:
            word += char

  if len(entities) > 0:
    corpus.append(entities)

  corpus = [" ".join(entity)  for entity in corpus]

  return corpus