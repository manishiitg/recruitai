import copy
from app.qa.util import get_page_and_box_map, get_section_match_map, get_resolved_section_match_map, do_section_identification_down, do_up_section_identification, create_combined_section_content_map, do_subsection_identification, get_orphan_section_map, validate, get_tags_subsections_subanswers, merge_orphan_to_ui, get_page_content_from_compressed_content, get_nlp_sentences
from app.account import initDB, get_cloud_bucket, connect_redis
from flair.models import SequenceTagger
import json
from app.qa.util import get_short_answer, get_fast_search_space
import warnings
from app.qa.util import clean_page_content_map
import subprocess
import sys
from pathlib import Path
import traceback
import time
from bson.objectid import ObjectId
from pymongo import MongoClient
import os
from app.config import BASE_PATH
from app.publishdatasync import sendMessage as datasync
from transformers import BartTokenizer, BartForConditionalGeneration, pipeline
import torch
from app.logging import logger
from app.qa.util_parts import get_new_section_map as parts_get_new_section_map, combine_new_section_map as parts_combine_new_section_map, get_tags_subsections_subanswers as parts_get_tags_subsections_subanswers

torch_device = 'cuda' if torch.cuda.is_available() else 'cpu'

question_answerer = None
max_model_seq_len = 4096


# from app.config import storage_client

warnings.simplefilter(action='ignore', category=FutureWarning)

questions_tag_mapping = {
    "personal_name": "Name",
    "summary": "Objective/Executive Summary",
    "total_experiance": "Total Experiance",
    "exp_company": "Recent Organization",
    "exp_designation": "Designation",
    "exp_duration": "Recent Duration",
    "projects_name": "Project Name",
    "skills": "Core Skills",
    "education_degree": "Degree",
    "education_year": "Passout Year",
    "certifications": "Certifications",
    "training": "Training",
    "personal_location": "Location",
    "personal_dob": "Date of Birth",
    "awards": "Awards",
    "extra": "Extra Curricular",
    "references": "References",
    "hobbies": "Hobbies"
}
questions_ordering = [
    "total_experiance",
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
    "total_experiance": "how much total experience do you have?",
    "exp_company": "which company did you work with most recently?",
    "exp_designation": "what was your most recent designation",
    "exp_duration": "what was the duration of your employment in your recent company?",
    # "exp_res": "what are your recent job responsibilities",
    "projects_name": "what is your most recent project",
    # "projects_skills": "what skillset or technologies you have used in your most recent projects?",
    "skills": "what are your skills or area of expertise?",
    "education_degree": "what is your education qualification",
    "education_year": "when year did you passout?",
    "certifications": "have you done any certifications",
    "training": "have you done any trainings",
    "personal_location": "where do you live",
    "personal_dob": "what is your date of birth",
    "awards": "any accomplishments or carrier highlights or awards?",
    "extra": "what are your extra curricular activatives",
    "references": "do you have any references",
    "hobbies": "what are you hobbies",
}
questions_needed_for_initial_data = [
    "personal_name", 
    "total_experiance",
    "exp_company",
    # "exp_designation", # this will come from ner
    # "exp_duration", # this will come from ner
    "projects_name",
    "skills",
    "education_degree",  # will fetch this from ner itself
    # "education_year", # will fetch this from ner itself
    # "certifications",
    "training",
    # "personal_location", # will fetch this from ner itself
    # "personal_dob", # will fetch this from ner itself
    # "awards"
]

questions_minimal = [
    "exp_company",
    "skills",
    "personal_name"
]


# this is for mini parsing
def get_short_answer_senctence(idx, account_name, account_config):
    db = initDB(account_name, account_config)
    if not ObjectId.is_valid(idx):
        logger.critical(f"invalid id {idx}")
        return {
            "error": f"invalid id {idx}"
        }

    row = db.emailStored.find_one({
        "_id": ObjectId(idx)
    })
    error = None
    if row:
        if "cvParsedInfo" in row:
            if "page_contents" in row["cvParsedInfo"]:
                page_contents = row["cvParsedInfo"]["page_contents"]
            else:
                error = {
                    "error": "page contents not found"
                }
        else:
            error = {
                "error": "cv parse info not found"
            }
    else:
        error = {
            "error": "mongo id not found"
        }

    if error:
        logger.critical(error)
        return

    if page_contents:
        page_content_map = {}
        bbox_map = {}
        exist_answer_map = {}

        if "cvParsedInfo" in row:
            cvParsedInfo = row["cvParsedInfo"]
            if "answer_map" in cvParsedInfo:
                exist_answer_map[str(row["_id"])] = cvParsedInfo["answer_map"]
            else:
                exist_answer_map[str(row["_id"])] = {}

            bbox_map[str(row["_id"])
                     ] = row["cvParsedInfo"]["newCompressedStructuredContent"]

        logger.critical("asking question %s", exist_answer_map)
        if len(page_contents) > 2:
            page_contents = page_contents[:1]
            # for mini parsing only first 2 page max
        
        page_content_map = clean_page_content_map(idx, page_contents)

        is_page_content_corrupt = False
        if not page_content_map:
            # this mean some issue with data. 
            logger.critical("issue with data for sure!")
            is_page_content_corrupt = True
            page_content_map = get_page_content_from_compressed_content(idx, account_name, account_config)
            if not page_content_map:
                return None

        answer_map = ask_question(
            idx, page_content_map, True, exist_answer_map, True)

        finalEntity, qa_short_answers, fast_search_space = get_fast_tags(
            idx, answer_map, page_content_map, row, questions_minimal)

        db.emailStored.update_one({
            "_id": ObjectId(idx)
        }, {
            '$set': {
                "cvParsedInfo.qa_type": "mini",
                "cvParsedInfo.qa_short_answers": qa_short_answers[idx],
                "cvParsedInfo.qa_fast_search_space": fast_search_space[idx],
                "cvParsedInfo.finalEntity": finalEntity
            }
        })


def get_fast_tags(idx, answer_map, page_content_map, row, questions, parsing_type="mini"):
    qa_short_answers = get_short_answer(answer_map, page_content_map)
    finalEntity = {}
    fast_search_space = {}
    if parsing_type != "full":
        tagger = loadTaggerModel()
        fast_search_space = get_fast_search_space(
            answer_map, page_content_map, tagger, questions)
        
        
        if "cvParsedInfo" in row:
            cvParsedInfo = row["cvParsedInfo"]
            if "finalEntity" in cvParsedInfo:
                finalEntity = cvParsedInfo["finalEntity"]

        for answer_key in fast_search_space[idx]:
            if answer_key == "exp_company" or "personal_" in answer_key:
                if 'tags' in fast_search_space[idx][answer_key]:
                    tags = fast_search_space[idx][answer_key]["tags"]
                    finalEntity = extract_final_entity_work(tags, finalEntity)



            
    return finalEntity, qa_short_answers, fast_search_space


def extract_final_entity_work(tags, finalEntity, only_first = True):

    tags = copy.deepcopy(tags)
    if len(tags) > 0:
        finalEntity['wrkExp'] = []
        orphan_designation = ""
        orphan_date = ""
        if "Designation" in finalEntity:
            del finalEntity['Designation']
        if "ExperianceYears" in finalEntity:
            del finalEntity['ExperianceYears']
        for tag in tags:
            # we won't be adding Additional etc here. as this is fast search. so only latest is needed
            tag["after_qa"] = 1
            if tag["label"] == "ORG":
                tag['org'] = tag['text']
                if len(orphan_designation) > 0:
                    tag["Designation"] = orphan_designation
                    orphan_designation = ""

                if len(orphan_date) > 0:
                    tag["DATE"] = orphan_date
                    orphan_date = ""

                finalEntity['wrkExp'].append([tag])
            if tag["label"] == "Designation" and 'Designation' not in finalEntity:
                if len(finalEntity['wrkExp']) > 0:
                    finalEntity['wrkExp'][0][-1]["Designation"] = tag["text"]
                else:
                    orphan_designation = tag["text"]
                finalEntity['Designation'] = tag
                if 'additional-Designation' in finalEntity:
                    del finalEntity['additional-Designation']

            if tag["label"] == "DATE":
                if len(finalEntity['wrkExp']) > 0:
                    finalEntity['wrkExp'][0][-1]["DATE"] = tag["text"]
                else:
                    orphan_date = tag["text"]
    else:
        if "wrkExp" in finalEntity:
            del finalEntity['wrkExp']

        if "Designation" in finalEntity:
            del finalEntity['Designation']
    
    return finalEntity

def extract_final_entity_personal_corrupt(tags, finalEntity, answer_map):
    
    if "personal_name" in answer_map:
        if "error" not in answer_map["personal_name"]:
            if len(answer_map["personal_name"]['answer']) > 0:
                finalEntity['PERSON'] = answer_map["personal_name"]['answer']
    
    if "personal_dob" in answer_map:
        if "error" not in answer_map["personal_dob"]:
            if len(answer_map["personal_dob"]['answer']) > 0:
                finalEntity['DOB'] = answer_map["personal_dob"]['answer']
    
    if "personal_location" in answer_map:
        if "error" not in answer_map["personal_location"]:
            if len(answer_map["personal_location"]['answer']) > 0:
                finalEntity['GPE'] = answer_map["personal_location"]['answer']
    
    return finalEntity

def qa_candidate_db(idx, only_initial_data, account_name, account_config, page_contents=None):
    db = initDB(account_name, account_config)
    if not ObjectId.is_valid(idx):
        logger.critical(f"invalid id {idx}")
        return {
            "error": f"invalid id {idx}"
        }
    error = None
    if not page_contents:
        row = db.emailStored.find_one({
            "_id": ObjectId(idx)
        })
        if row:
            if "cvParsedInfo" in row:
                if "page_contents" in row["cvParsedInfo"]:
                    page_contents = row["cvParsedInfo"]["page_contents"]
                else:
                    error = {
                        "error": "page contents not found"
                    }
            else:
                error = {
                    "error": "cv parse info not found"
                }
        else:
            error = {
                "error": "mongo id not found"
            }

        if error:
            logger.critical(error)

    if page_contents:

        page_content_map = {}
        bbox_map = {}

        db = initDB(account_name, account_config)
        exist_answer_map = {}
        # candidate_row = db.emailStored.find_one({"_id": ObjectId(idx)})
        if "cvParsedInfo" in row:
            cvParsedInfo = row["cvParsedInfo"]
            if "answer_map" in cvParsedInfo:
                exist_answer_map[str(row["_id"])] = cvParsedInfo["answer_map"]
            else:
                exist_answer_map[str(row["_id"])] = {}
            
            
            if "qa_type" in row:
                qa_type = row["qa_type"]
                if qa_type == "mini":
                    exist_answer_map[str(row["_id"])] = {} 
                    print("#discard mini answers are mini we are fetching only with first 2 pages")
                    # experimental

            bbox_map[str(row["_id"])] = row["cvParsedInfo"]["newCompressedStructuredContent"]

        logger.critical("asking question %s", exist_answer_map)

        page_content_map = clean_page_content_map(idx, page_contents)
        is_page_content_corrupt = False
        if not page_content_map:
            # this mean some issue with data. 
            
            logger.critical("issue with data for sure!")
            is_page_content_corrupt = True
            page_content_map = get_page_content_from_compressed_content(idx, account_name, account_config)
            if not page_content_map:
                return None

        answer_map = ask_question(
            idx, page_content_map, only_initial_data, exist_answer_map, False)
        if not answer_map:
            logger.critical("error: some problem with page content")
            db.emailStored.update_one({
                "_id": ObjectId(idx)
            }, {
                '$set': {
                    "cvParsedInfo.answer_map": {"error": "page_content issue"}
                }
            })
            return

        logger.critical(answer_map)

        db.emailStored.update_one({
            "_id": ObjectId(idx)
        }, {
            '$set': {
                "cvParsedInfo.answer_map": answer_map[idx]
            }
        })

        if only_initial_data:
            finalEntity, qa_short_answers, fast_search_space = get_fast_tags(
                idx, answer_map, page_content_map, row, questions_needed_for_initial_data)
            db.emailStored.update_one({
                "_id": ObjectId(idx)
            }, {
                '$set': {
                    "cvParsedInfo.qa_type": "fast",
                    "cvParsedInfo.qa_short_answers": qa_short_answers[idx],
                    "cvParsedInfo.qa_fast_search_space": fast_search_space[idx],
                    "cvParsedInfo.finalEntity": finalEntity
                }
            })
        else:
            final_section_ui_map = parse_resume(idx, answer_map, page_content_map,
                                                bbox_map, account_name, account_config)

            if not final_section_ui_map:
                return 
                

            finalEntity, qa_short_answers, fast_search_space = get_fast_tags(
                idx, answer_map, page_content_map, row, list(questions.keys()) , "full")

            finalEntity = {}
            if "cvParsedInfo" in row:
                cvParsedInfo = row["cvParsedInfo"]
                if "finalEntity" in cvParsedInfo:
                    finalEntity = cvParsedInfo["finalEntity"]

            all_work_tags = []
            all_personal_tags = []
            for answer_key in final_section_ui_map[idx]:
                if "exp_" in answer_key :
                    for row in final_section_ui_map[idx][answer_key]:
                        if "tags" in row:
                            if len(row["tags"]) > 0:
                                all_work_tags.extend(row["tags"])
                if "personal_" in answer_key:
                    for row in final_section_ui_map[idx][answer_key]:
                        if "tags" in row:
                            if len(row["tags"]) > 0:
                                all_personal_tags.extend(row["tags"])
            
            if len(all_work_tags) > 0:
                finalEntity = extract_final_entity_work(all_work_tags, finalEntity)

            if is_page_content_corrupt and len(all_personal_tags) > 0:
                finalEntity = extract_final_entity_personal_corrupt(all_personal_tags, finalEntity, answer_map[idx])
            
            db.emailStored.update_one({
                "_id": ObjectId(idx)
            }, {
                '$set': {
                    "cvParsedInfo.qa_short_answers": qa_short_answers[idx],
                    "cvParsedInfo.finalEntity": finalEntity
                }
            })
    else:
        logger.critical("error %s", error)


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
            "_id": ObjectId(idx)
        }, {
            '$set': {
                "cvParsedInfo.debug.qa_parse_resume.error": "all answers are empty check page content"
            }
        })
        return

    db.emailStored.update_one({
        "_id": ObjectId(idx)
    }, {
        '$set': {
            "cvParsedInfo.qa_parse_resume": {}
        }
    })

    bbox_map_int, page_box_count = get_page_and_box_map(bbox_map)
    logger.info(json.dumps(page_box_count, indent=True))

    section_match_map = get_section_match_map(
        answer_map, bbox_map_int, page_box_count, page_content_map)
    logger.info(json.dumps(section_match_map, indent=True))

    # db.emailStored.update_one({
    #     "_id" : ObjectId(idx)
    # }, {
    #     '$set' : {
    #         "cvParsedInfo.debug.qa_parse_resume.section_match_map" : section_match_map[idx]
    #     }
    # })
    

    new_section_match_map = get_resolved_section_match_map(section_match_map)
    logger.info(json.dumps(new_section_match_map, indent=True))

    # db.emailStored.update_one({
    #     "_id" : ObjectId(idx)
    # }, {
    #     '$set' : {
    #         "cvParsedInfo.debug.qa_parse_resume.new_section_match_map" : new_section_match_map[idx]
    #     }
    # })

    section_content_map, absorbed_map, full_question_key_absorted = do_section_identification_down(
        new_section_match_map, bbox_map_int, page_box_count)
    logger.info(json.dumps(section_content_map, indent=True))

    # db.emailStored.update_one({
    #     "_id" : ObjectId(idx)
    # }, {
    #     '$set' : {
    #         "cvParsedInfo.debug.qa_parse_resume.section_content_map" : section_content_map[idx]
    #     }
    # })

    # print(idx)
    validate(new_section_match_map, section_content_map,
             full_question_key_absorted)

    up_section_content_map, up_absorbed_map = do_up_section_identification(
        new_section_match_map, bbox_map_int, page_box_count, absorbed_map)
    logger.info(json.dumps(up_section_content_map, indent=True))

    # db.emailStored.update_one({
    #     "_id" : ObjectId(idx)
    # }, {
    #     '$set' : {
    #         "cvParsedInfo.debug.qa_parse_resume.up_section_content_map" : up_section_content_map[idx]
    #     }
    # })

    combined_section_content_map = create_combined_section_content_map(
        section_content_map, up_section_content_map)
    logger.info(json.dumps(combined_section_content_map, indent=True))

    # db.emailStored.update_one({
    #     "_id" : ObjectId(idx)
    # }, {
    #     '$set' : {
    #         "cvParsedInfo.debug.qa_parse_resume.combined_section_content_map" : combined_section_content_map[idx]
    #     }
    # })

    complete_section_match_map, complete_absorbed_map = do_subsection_identification(
        combined_section_content_map, absorbed_map, up_absorbed_map, answer_map, bbox_map_int, page_box_count)
    logger.info(json.dumps(complete_section_match_map, indent=True))

    orphan_section_map = get_orphan_section_map(
        answer_map, bbox_map_int, absorbed_map, up_absorbed_map, complete_absorbed_map)

    # print(json.dumps(combined_section_content_map, indent=True))
    logger.info("=====================complete_section_match_map------------------=====")
    logger.info(json.dumps(complete_section_match_map, indent=True))
    logger.info("========================== complete_section_match_map end ===================")
    logger.info(json.dumps(orphan_section_map, indent=True))
    if len(list(orphan_section_map.keys())) != 0:
        logger.critical("orphan has keys!")  # pass nothing else to do
        # assert(len(list(orphan_section_map.keys())) == 0)

    tagger = loadTaggerModel()
    question_answerer = loadModel()
    section_ui_map = get_tags_subsections_subanswers(
        complete_section_match_map, tagger, question_answerer)

    final_section_ui_map = merge_orphan_to_ui(
        section_ui_map, orphan_section_map, page_box_count, tagger)

    logger.info(final_section_ui_map)
    db.emailStored.update_one({
        "_id": ObjectId(idx)
    }, {
        '$set': {
            "cvParsedInfo.qa_type": "full",
            "cvParsedInfo.qa_parse_resume": final_section_ui_map[idx]
        }
    })

    classifier = loadClassifierModel()
    new_section_map = parts_get_new_section_map(final_section_ui_map, classifier)
    complete_section_match_map = parts_combine_new_section_map(new_section_map)
    complete_section_match_map = parts_get_tags_subsections_subanswers(complete_section_match_map, tagger)
#   
    db.emailStored.update_one({
        "_id": ObjectId(idx)    
    }, {
        '$set': {
            "cvParsedInfo.qa_type": "full",
            "cvParsedInfo.complete_section_match_map": complete_section_match_map[idx]
        }
    })

    logger.critical("=======================complete_section_match_map===========================")
    logger.critical(json.dumps(complete_section_match_map, indent=1))
    logger.critical("=======================complete_section_match_map===========================")
    

    return final_section_ui_map

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


def ask_question(idx, page_content_map, only_initial_data=False, exist_answer_map={}, is_mini=False):
    

    logger.critical(f"only_initial_data {only_initial_data}  is_mini {is_mini} ")

    answer_map = {}

    for idx in page_content_map:
        page_content = page_content_map[idx]
        answer_map[idx] = {}
        logger.critical("==================================")
        # logger.critical(page_content)

        max_seq_len = len(page_content)
        if max_seq_len > max_model_seq_len:
            max_seq_len = max_model_seq_len
            if only_initial_data or is_mini:
                page_content = page_content[:max_seq_len-1]
            
            if len(page_content) > 2 * max_seq_len:
                page_content = page_content[:(2 *max_seq_len)-1] # there few cv having more 60k characters?!!!! ad it takes 3 min per ques

        logger.critical(f"max seq len {max_seq_len}")
        skip_question = []

        for key in questions:
            question = questions[key]

            if key in exist_answer_map[idx]:
                if exist_answer_map[idx][key]["question"] == questions[key]:
                    logger.critical("answer already exists for question %s", key)
                    answer_map[idx][key] = exist_answer_map[idx][key]
                    answer = exist_answer_map[idx][key]
                    if "error" in answer:
                        continue
                    if key == "exp_company":
                        if len(answer["answer"]) == 0:
                            skip_question.extend(
                                ["exp_designation", 'exp_duration'])

                        # else:
                        #     skip_question.extend(["projects_name",'certifications','training','awards'])
                        # even for experiances ppl we need to ask these questions

                    if key == "projects_desc":
                        if len(answer["answer"]) == 0:
                            skip_question.extend(["projects_skills"])

                    continue

            if is_mini:
                if key not in questions_minimal:
                    continue
            elif only_initial_data:
                if key not in questions_needed_for_initial_data:
                    continue

            start_time = time.time()
            if key in skip_question:
                continue

            try:

                answer = question_answerer({
                    'question': question,
                    'context': page_content
                }, handle_impossible_answer=True, max_seq_len=max_seq_len, doc_stride=328)

                if key == "exp_company":
                    if len(answer["answer"]) == 0:
                        skip_question.extend(
                            ["exp_designation", 'exp_duration'])

                    # else:
                    #     skip_question.extend(["projects_name",'certifications','training','awards'])
                    # even for experiances ppl we need to ask these questions

                if key == "projects_desc":
                    if len(answer["answer"]) == 0:
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
            # break #temp

    return answer_map


def loadModel():
    global question_answerer

    if question_answerer is None:
        logger.critical("gpu %s", torch.cuda.is_available())
        if torch.cuda.is_available():
            question_answerer = pipeline(
                'question-answering', device=0, model="manishiitg/longformer-recruit-qa", tokenizer="manishiitg/longformer-recruit-qa")
        else:
            question_answerer = pipeline(
                'question-answering', device=-1, model="manishiitg/longformer-recruit-qa", tokenizer="manishiitg/longformer-recruit-qa")

    return question_answerer


tagger = None


def loadTaggerModel():
    global tagger
    if tagger is None:
        logger.critical("loading tagger model")
        tagger = SequenceTagger.load(
            "/workspace/recruit-tags-flair-roberta-word2vec/recruit-tags-flair-roberta-word2vec/best-model.pt")
        logger.critical("model tagger loaded")
    return tagger

classifier = None

def loadClassifierModel():
    global classifier
    if classifier is None:
        if torch.cuda.is_available():
            classifier = pipeline('sentiment-analysis', "manishiitg/distilbert-resume-parts-classify", device=0)
        else:
            classifier = pipeline('sentiment-analysis', "manishiitg/distilbert-resume-parts-classify")

    return classifier