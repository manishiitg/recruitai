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

questions_tag_mapping = {
  "personal_name": "Name",
  "summary": "Objective/Executive Summary",
  "exp_years":"Total Experiance",
  "exp_company": "Recent Organization",
  "exp_designation": "Designation",
  "exp_duration": "Recent Duration",
  "projects_name":"Project Name",
  "skills": "Core Skills",
  "education_degree": "Degree",
  "education_year": "Passout Year",
  "certifications": "Certifications",
  "training": "Training",
  "personal_location":"Location",
  "personal_dob":"Date of Birth",
  "awards": "Awards",
  "extra":"Extra Curricular",
  "references" : "References",
  "hobbies" : "Hobbies"
}
questions_ordering = [
  "exp_years",
  "exp_company",
  "exp_designation",
  "exp_duration",
  "projects_name",
  "skills",
  "education_degree",
  "education_year",
  "certifications",
  "training",
  "awards",
  "personal_name",
  "summary",
  "personal_location",
  "personal_dob",
  "extra",
  "references"
]

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
  "references" : "do you have any references",
  "hobbies" : "what are you hobbies",
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
    if not ObjectId.is_valid(idx):
        logger.critical(f"invalid id {idx}")
        return {
            "error" : f"invalid id {idx}"
        }
    error = None
    if not page_contents:
        row = db.emailStored.find_one({
            "_id" : ObjectId(idx)
        })
        if row:
            if "cvParsedInfo" in row:
                if "page_contents" in row["cvParsedInfo"]:
                    page_contents = row["cvParsedInfo"]["page_contents"]
                else:
                    error = {
                        "error" : "page contents not found"
                    }    
            else:
                error = {
                    "error" : "cv parse info not found"
                }
        else:
            error = {
                    "error" : "mongo id not found"
                }        
        
        if error:
            logger.critical(error)

    if page_contents:

        page_content_map = {}
        bbox_map = {}

        db = initDB(account_name, account_config)
        exist_answer_map = {}
        candidate_row = db.emailStored.find_one({"_id" : ObjectId(idx)})
        if "cvParsedInfo" in candidate_row:
            cvParsedInfo = candidate_row["cvParsedInfo"]
            if "answer_map" in cvParsedInfo:
                exist_answer_map[str(row["_id"])] = cvParsedInfo["answer_map"]
            else:
                exist_answer_map[str(row["_id"])] = {}

            bbox_map[str(row["_id"])] = row["cvParsedInfo"]["newCompressedStructuredContent"]

        logger.critical("asking question %s", exist_answer_map)

        page_content_map = clean_page_content_map(idx, page_contents)
        

        answer_map = ask_question(idx, page_contents, only_initial_data, exist_answer_map)
        if not answer_map:
            logger.critical("error: some problem with page content")
            db.emailStored.update_one({
                "_id" : ObjectId(idx)
            }, {
                '$set' : {
                    "cvParsedInfo.answer_map" : {"error":"page_content issue"}
                }
            })
            return 

        logger.critical(answer_map)
        
        db.emailStored.update_one({
            "_id" : ObjectId(idx)
        }, {
            '$set' : {
                "cvParsedInfo.answer_map" : answer_map[idx]
            }
        })

        parse_resume(idx, answer_map, page_content_map, bbox_map, account_name, account_config)
    else:
        logger.critical("error %s", error)

from app.qa.util import get_page_and_box_map, get_section_match_map, get_resolved_section_match_map, do_section_identification_down, do_up_section_identification, create_combined_section_content_map, do_subsection_identification, get_orphan_section_map, validate, get_tags_subsections_subanswers, merge_orphan_to_ui
import json
import traceback


def parse_resume(idx, answer_map, page_content_map, bbox_map, account_name, account_config):
    db = initDB(account_name, account_config)

    # try:
    are_all_answers_empty = True
    for idxxxx in answer_map:
        answers = answer_map[idxxxx]

        for key in answers:
            if "error" in answers[key]:
                continue
            print(f"key {key} answer: {answers[key]['answer']}")
            if len(answers[key]["answer"]) != 0:
                are_all_answers_empty = False
    
    if are_all_answers_empty:
        logger.critical("all answers are empty")
        db.emailStored.update_one({
            "_id" : ObjectId(idx)
        }, {
            '$set' : {
                "cvParsedInfo.debug.qa_parse_resume.error" : "all answers are empty check page content"
            }
        })
        return 

    db.emailStored.update_one({
        "_id" : ObjectId(idx)
    }, {
        '$set' : {
            "cvParsedInfo.debug.qa_parse_resume" : {}
        }
    })

    bbox_map_int, page_box_count = get_page_and_box_map(bbox_map)
    logger.info(json.dumps(page_box_count, indent=True))

    

    section_match_map = get_section_match_map(answer_map, bbox_map_int, page_box_count, page_content_map)
    logger.info(json.dumps(section_match_map, indent = True))

    # db.emailStored.update_one({
    #     "_id" : ObjectId(idx)
    # }, {
    #     '$set' : {
    #         "cvParsedInfo.debug.qa_parse_resume.section_match_map" : section_match_map[idx]
    #     }
    # })

    new_section_match_map = get_resolved_section_match_map(section_match_map)
    logger.info(json.dumps(new_section_match_map, indent = True))

    # db.emailStored.update_one({
    #     "_id" : ObjectId(idx)
    # }, {
    #     '$set' : {
    #         "cvParsedInfo.debug.qa_parse_resume.new_section_match_map" : new_section_match_map[idx]
    #     }
    # })

    section_content_map , absorbed_map, full_question_key_absorted = do_section_identification_down(new_section_match_map, bbox_map_int, page_box_count)
    logger.info(json.dumps(section_content_map, indent=True))

    # db.emailStored.update_one({
    #     "_id" : ObjectId(idx)
    # }, {
    #     '$set' : {
    #         "cvParsedInfo.debug.qa_parse_resume.section_content_map" : section_content_map[idx]
    #     }
    # })

    validate(new_section_match_map, section_content_map, full_question_key_absorted)

    up_section_content_map, up_absorbed_map= do_up_section_identification(new_section_match_map, bbox_map_int, page_box_count, absorbed_map)
    logger.info(json.dumps(up_section_content_map, indent=True))

    # db.emailStored.update_one({
    #     "_id" : ObjectId(idx)
    # }, {
    #     '$set' : {
    #         "cvParsedInfo.debug.qa_parse_resume.up_section_content_map" : up_section_content_map[idx]
    #     }
    # })

    combined_section_content_map = create_combined_section_content_map(section_content_map, up_section_content_map)
    logger.info(json.dumps(combined_section_content_map, indent=True))

    # db.emailStored.update_one({
    #     "_id" : ObjectId(idx)
    # }, {
    #     '$set' : {
    #         "cvParsedInfo.debug.qa_parse_resume.combined_section_content_map" : combined_section_content_map[idx]
    #     }
    # })

    complete_section_match_map, complete_absorbed_map = do_subsection_identification(combined_section_content_map, absorbed_map, up_absorbed_map, answer_map, bbox_map_int, page_box_count)
    logger.info(json.dumps(complete_section_match_map, indent=True))

    orphan_section_map = get_orphan_section_map(answer_map, bbox_map_int, absorbed_map, up_absorbed_map, complete_absorbed_map)

    # print(json.dumps(combined_section_content_map, indent=True))
    logger.info("==========================")
    logger.info(json.dumps(complete_section_match_map, indent=True))
    logger.info("==========================")
    logger.info(json.dumps(orphan_section_map, indent=True))
    if len(list(orphan_section_map.keys())) != 0:
        logger.critical("orphan has keys!") # pass nothing else to do
        # assert(len(list(orphan_section_map.keys())) == 0)

    tagger = loadTaggerModel()
    question_answerer = loadModel()
    section_ui_map = get_tags_subsections_subanswers(complete_section_match_map, tagger, question_answerer)

    final_section_ui_map = merge_orphan_to_ui(section_ui_map, orphan_section_map, page_box_count, tagger)

    logger.info(section_ui_map)
    db.emailStored.update_one({
        "_id" : ObjectId(idx)
    }, {
        '$set' : {
            "cvParsedInfo.qa_parse_resume" : final_section_ui_map[idx]
        }
    })

    # except Exception as e:
    #     traceback.print_exc()
    #     db.emailStored.update_one({
    #         "_id" : ObjectId(idx)
    #     }, {
    #         '$set' : {
    #             "cvParsedInfo.debug.qa_parse_resume.error" : str(e)
    #         }
    #     })
    #     logger.critical(e)
        

def ask_question(idx, page_contents, only_initial_data = False, exist_answer_map = {}):

    page_content_map = clean_page_content_map(idx, page_contents)


    if not page_content_map:
        return None

    answer_map = {}


    
    for idx in page_content_map:
        page_content = page_content_map[idx]
        answer_map[idx] = {}
        logger.critical("==================================")
        logger.critical(page_content)


        max_seq_len = len(page_content)
        if max_seq_len > max_model_seq_len:
            max_seq_len = max_model_seq_len

        logger.critical(f"max seq len {max_seq_len}")
        skip_question = []
        

        for key in questions:
            question = questions[key]
            if only_initial_data:
                if key not in questions_needed_for_initial_data:
                    continue
            
            if key in exist_answer_map[idx]:
                logger.critical("answer already exists for question %s", key)
                answer_map[idx][key] = exist_answer_map[idx][key]
                continue

            start_time = time.time()
            if key in skip_question:
                continue
            
            try:
            
                answer = question_answerer({
                            'question': question,
                            'context': page_content
                        },handle_impossible_answer = True, max_seq_len = max_seq_len, doc_stride = 328) 
            

                if key == "exp_company":
                    if len(answer["answer"]) == 0:
                        skip_question.extend(["exp_designation",'exp_duration'])
                    else:
                        skip_question.extend(["projects_name",'certifications','training','awards'])

                if key == "projects_desc" and len(answer["answer"]) == 0:
                    skip_question.extend(["projects_skills"])

                
                answer["question"] = question
                answer["question_key"] = key
                answer["time_taken"] = time.time() - start_time
                answer_map[idx][key] = answer

                
                logger.critical(question)
                logger.critical(answer)

            except Exception as e:
                print("exception ", str(e))
                answer_map[idx][key] = {"error": str(e), "question": question}
                pass

            logger.critical(f"==================== {time.time() - start_time}")

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

tagger = None
from flair.models import SequenceTagger

def loadTaggerModel():
    global tagger
    if tagger is None:
        logger.critical("loading tagger model")
        tagger = SequenceTagger.load("/workspace/recruit-tags-flair-roberta-word2vec/recruit-tags-flair-roberta-word2vec/best-model.pt")
        logger.critical("model tagger loaded")
    return tagger