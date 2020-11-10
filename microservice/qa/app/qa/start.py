from transformers import BartTokenizer, BartForConditionalGeneration, pipeline
import torch
from app.logging import logger

torch_device = 'cuda' if torch.cuda.is_available() else 'cpu'

question_answerer = None
max_model_seq_len = 4096

from app.publishdatasync import sendMessage as datasync

from app.config import BASE_PATH
import os
from pymongo import MongoClient
from bson.objectid import ObjectId
import time
import traceback

from app.account import initDB, get_cloud_bucket , connect_redis

from pathlib import Path

import sys
# from app.config import storage_client
import subprocess
from pathlib import Path
import time
from app.qa.util import clean_page_content_map

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

questions = {
  "personal_name": "what is your name?",
  "summary": "what is your career objective or executive summary",
  "exp_years":"how much total experience do you have?",
  "exp_company": "which company did you work with most recently?",
  "exp_designation": "what was your most recent designation",
  "exp_duration": "what was the duration of your employment in your recent company?",
  # "exp_res": "what are your recent job responsibilities",
  "projects_name":"what is your most recent project",
  # "projects_skills": "what skillset or technologies you have used in your most recent projects?",
  "skills": "what are your skills or area of expertise?",
  "education_degree": "what is your education qualification",
  "education_year": "when year did you passout?",
  "certifications": "have you done any certifications",
  "training": "have you done any trainings",
  "personal_location":"where do you live",
  "personal_dob":"what is your date of birth",
  "awards": "any accomplishments or carrier highlights or awards?",
  "extra":"what are your favorite extra curricular activatives or hobbies",
  "references" : "do you have any references"
}
questions_needed_for_initial_data = [
    # "personal_name", # will fetch this from ner itself
    "exp_years",
    "exp_company",
    "exp_designation",
    "exp_duration",
    "projects_name",
    "skills",
    "education_degree", # will fetch this from ner itself
    # "education_year", # will fetch this from ner itself
    # "certifications",
    "training",
    # "personal_location", # will fetch this from ner itself
    # "personal_dob", # will fetch this from ner itself
    # "awards"
]

def qa_candidate_db(idx, only_initial_data, account_name, account_config, page_contents = None):
    db = initDB(account_name, account_config)
    
    error = None
    if not page_contents:
        row = db.emailStored.find_one({
            "_id" : ObjectId(idx)
        })
        if "cvParsedInfo" in row:
            if "debug" in row["cvParsedInfo"]:
                if "page_contents" in row["cvParsedInfo"]["debug"]:
                    page_contents = row["cvParsedInfo"]["debug"]["page_contents"]
                else:
                    error = {
                        "error" : "page contents not found"
                    }
            else:
                error = {
                    "error" : "debug not found"
                }    
        else:
            error = {
                "error" : "cv parse info not found"
            }

    if page_contents:

        db = initDB(account_name, account_config)
        exist_answer_map = {}
        candidate_row = db.emailStored.find_one({"_id" : ObjectId(idx)})
        if "cvParsedInfo" in candidate_row:
            cvParsedInfo = candidate_row["cvParsedInfo"]
            if "answer_map" in cvParsedInfo:
                exist_answer_map = cvParsedInfo["answer_map"]


        answer_map = ask_question(idx, page_contents, only_initial_data, exist_answer_map)
        if not answer_map:
            logger.info("error: some problem with page content")
            db.emailStored.update_one({
                "_id" : ObjectId(idx)
            }, {
                '$set' : {
                    "cvParsedInfo.answer_map" : {"error":"page_content issue"}
                }
            })
            return 

        logger.info(answer_map)
        
        db.emailStored.update_one({
            "_id" : ObjectId(idx)
        }, {
            '$set' : {
                "cvParsedInfo.answer_map" : answer_map[idx]
            }
        })
    else:
        logger.info("error %s", error)


def ask_question(idx, page_contents, only_initial_data = True, exist_answer_map = {}):

    page_content_map = clean_page_content_map(idx, page_contents)


    if not page_content_map:
        return None

    answer_map = {}


    
    for idx in page_content_map:
        page_content = page_content_map[idx]
        answer_map[idx] = {}
        logger.info("==================================")
        logger.info(page_content)


        max_seq_len = len(page_content)
        if max_seq_len > max_model_seq_len:
            max_seq_len = max_model_seq_len

        logger.info(f"max seq len {max_seq_len}")
        skip_question = []
        

        for key in questions:
            question = questions[key]
            if only_initial_data:
                if key not in questions_needed_for_initial_data:
                    continue
            
            if key in exist_answer_map:
                logger.critical("anser already exists for question %s", key)
                continue

            start_time = time.time()
            if key in skip_question:
                continue
            
            try:
            
                answer = question_answerer({
                            'question': question,
                            'context': page_content
                        },handle_impossible_answer = True, max_seq_len = max_seq_len, doc_stride = 328) 
            

                if key == "exp_company" and len(answer["answer"]) == 0:
                    skip_question.extend(["exp_designation",'exp_duration'])
                else:
                    skip_question.extend(["projects_name",'certifications','training','awards'])

                if key == "projects_desc" and len(answer["answer"]) == 0:
                    skip_question.extend(["projects_skills"])

                
                answer["question"] = question
                answer["question_key"] = key
                answer["time_taken"] = time.time() - start_time
                answer_map[idx][key] = answer

                
                logger.info(question)
                logger.info(answer)

            except Exception as e:
                print("exception ", str(e))
                answer_map[idx][key] = {"error": str(e), "question": question}
                pass

            logger.info(f"==================== {time.time() - start_time}")

    return answer_map



def loadModel():
    global question_answerer

    logger.critical("gpu %s", torch.cuda.is_available())
    if question_answerer is None:
        if torch.cuda.is_available():
            question_answerer = pipeline('question-answering', device = 0, model="manishiitg/longformer-recruit-qa", tokenizer="manishiitg/longformer-recruit-qa")
        else:
            question_answerer = pipeline('question-answering', device = -1, model="manishiitg/longformer-recruit-qa", tokenizer="manishiitg/longformer-recruit-qa")

    
    return question_answerer