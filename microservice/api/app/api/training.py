from app.logging import logger
from app import token
from flask import (
    Blueprint, flash, jsonify, abort, request, render_template, Response, redirect, send_from_directory
)

from bson.objectid import ObjectId
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)

bp = Blueprint('training', __name__, url_prefix='/training')

from pathlib import Path

from app.config import BASE_PATH, storage_client

import uuid

import os
import traceback
import sys
import json

from app.util import check_and_validate_account, get_resume_priority

import shutil

from app.publisher.resume import sendMessage
import time

from app.account import initDB, get_cloud_bucket, get_cloud_url

@bp.route("/resume/requeue/error", methods=["GET"])
@bp.route("/resume/requeue/error/<int:onlycount>", methods=["GET"])
@check_and_validate_account
def requeue_error(only_count = 0):
    db = initDB(request.account_name, request.account_config)

    if only_count == 1:
        count = db.emailStored.count({    
            "cvParsedInfo.error" : { "$exists" : True  }  , 
            "attachment.0.attachment.publicPath" : { "$exists" : True }  }
        )
        return jsonify({
            "count" : count
        })

    count = 0
    rows = db.emailStored.find({    
        "cvParsedInfo.error" : { "$exists" : True  }  , 
        "attachment.0.attachment.publicPath" : { "$exists" : True }  }
    ).limit(500)

    for row in rows:
        count += 1

        if "email_timestamp" not in row:
            row["email_timestamp"] = 0
        
        if row["email_timestamp"] == 'NaN':
            row["email_timestamp"] = 0

        priority, days, cur_time = get_resume_priority(int(row["email_timestamp"]) / 1000)
        obj = {
            "filename" : row["attachment"][0]["attachment"]["publicFolder"],
            "mongoid" : str(row["_id"]),
            "skills" : {},
            "meta" : {},
            "priority" : priority,
            "account_name": request.account_name,
            "account_config" : request.account_config
        }
        logger.info(obj)
        sendMessage(obj)
        time.sleep(.1)

    return jsonify({
        "cvParsedInfo_error_false_attachment_public_path_exist_true" : count
    })

@bp.route("/resume/requeue/parsing_fast", methods=["GET"])
@bp.route("/resume/requeue/parsing_fast/<int:only_count>", methods=["GET"])
@check_and_validate_account
def requeue_parsing_fast(only_count = 0):
    db = initDB(request.account_name, request.account_config)

    if only_count == 1:
        count = db.emailStored.count({    
            "cvParsedInfo.parsing_type" : "fast" , 
            "attachment.0.attachment.publicPath" : { "$exists" : True }  }
        )
        return jsonify({
            "count" : count
        })

    count = 0
    rows = db.emailStored.find({    
        "cvParsedInfo.parsing_type" : "fast" , 
        "attachment.0.attachment.publicPath" : { "$exists" : True }  }
    ).limit(1000)

    for row in rows:
        count += 1

        if "email_timestamp" not in row:
            row["email_timestamp"] = 0
        
        if row["email_timestamp"] == 'NaN':
            row["email_timestamp"] = 0

        priority, days, cur_time = get_resume_priority(int(row["email_timestamp"]) / 1000)
        obj = {
            "filename" : row["attachment"][0]["attachment"]["publicFolder"],
            "mongoid" : str(row["_id"]),
            "skills" : {},
            "meta" : {},
            "priority" : 1,
            "parsing_type" : "full",
            "account_name": request.account_name,
            "account_config" : request.account_config
        }
        logger.info(obj)
        sendMessage(obj)
        time.sleep(.1)

    return jsonify({
        "cvParsedInfo_error_false_attachment_public_path_exist_true" : count
    })

import random

@bp.route("/resume/requeue/random", methods=["GET"])
@bp.route("/resume/requeue/random/<int:limit>", methods=["GET"])
@bp.route("/resume/requeue/random/<int:limit>/<int:only_debug_missed>", methods=["GET"])
@check_and_validate_account
def requeue_random(limit = 1, only_debug_missed = 0):
    db = initDB(request.account_name, request.account_config)
    
    if only_debug_missed:
        count = db.emailStored.count({    
            "cvParsedInfo.debug.jsonOutputbbox": { "$exists" : False},
            "attachment.0.attachment.publicPath" : { "$exists" : True },
        }) 
        
        rows = db.emailStored.find({    
            "cvParsedInfo.debug.jsonOutputbbox": { "$exists" : False},
            "attachment.0.attachment.publicPath" : { "$exists" : True }  
        }).limit(limit).skip(random.randint(0, count))
        

    else:
        count = db.emailStored.count({    
            "attachment.0.attachment.publicPath" : { "$exists" : True },  }
        ) 
        
        rows = db.emailStored.find({    
            "attachment.0.attachment.publicPath" : { "$exists" : True }  }
        ).limit(limit).skip(random.randint(0, count))

    xcount = 0
    for row in rows:
        xcount += 1
        if "email_timestamp" not in row:
            row["email_timestamp"] = 0
        
        if row["email_timestamp"] == 'NaN':
            row["email_timestamp"] = 0

        priority, days, cur_time = get_resume_priority(int(row["email_timestamp"]) / 1000)
        obj = {
            "filename" : row["attachment"][0]["attachment"]["publicFolder"],
            "mongoid" : str(row["_id"]),
            "skills" : {},
            "parsing_type" : "full",
            "meta" : {},
            "priority" : priority,
            "account_name": request.account_name,
            "account_config" : request.account_config
        }
        logger.info(obj)
        sendMessage(obj)
        time.sleep(.05)

    return jsonify({
        "cvParsedInfo_random_attachment_public_path_exist_true" : count,
        "xcount" : xcount
    })

@bp.route("/resume/requeue/candidate/<string:candidate_id>", methods=["GET"])
@check_and_validate_account
def requeue_candidate(candidate_id):
    db = initDB(request.account_name, request.account_config)
    
    
    row = db.emailStored.find_one({    
        "_id" : ObjectId(candidate_id)
    })
    logger.info(row)

    count = 0
    count += 1
    priority, days, cur_time = get_resume_priority(int(row["email_timestamp"]) / 1000)
    obj = {
        "filename" : row["attachment"][0]["attachment"]["publicFolder"],
        "mongoid" : str(row["_id"]),
        "skills" : {},
        "meta" : {},
        "priority" : priority,
        "account_name": request.account_name,
        "account_config" : request.account_config,
    }
    logger.info(obj)
    sendMessage(obj)
    time.sleep(.05)
    
    return jsonify({
        "priority" : priority,
        "email_timestamp" : int(row["email_timestamp"]),
        "days" : days,
    })



@bp.route("/resume/requeue/missed", methods=["GET"])
@bp.route("/resume/requeue/missed/<int:only_count>", methods=["GET"])
@check_and_validate_account
def requeue(only_count = 0):
    db = initDB(request.account_name, request.account_config)
    if only_count == 1:
        count = db.emailStored.count({    
            "cvParsedInfo" : { "$exists" : False  }  , 
            "attachment.0.attachment.publicPath" : { "$exists" : True }  }
        )
        return jsonify({
            "count" : count
        })

    count = 0
    rows = db.emailStored.find({    
        "cvParsedInfo" : { "$exists" : False  }  , 
        "attachment.0.attachment.publicPath" : { "$exists" : True }  }
    ).limit(500)

    for row in rows:
        count += 1
        priority, days, cur_time = get_resume_priority(int(row["email_timestamp"]) / 1000)
        obj = {
            "filename" : row["attachment"][0]["attachment"]["publicFolder"],
            "mongoid" : str(row["_id"]),
            "skills" : {},
            "meta" : {},
            "priority" : priority,
            "account_name": request.account_name,
            "account_config" : request.account_config
        }
        logger.info(obj)
        sendMessage(obj)
        time.sleep(.05)

    return jsonify({
        "cvParsedInfo_exists_false_attachment_public_path_exist_true" : count
    })

@bp.route('/viz/get_with_pic_for_annotation', methods=['GET'])
@check_and_validate_account
def get_with_pic_for_annotation():
    db = initDB(request.account_name, request.account_config)

    rows = db.emailStored.find({"cvimage.picture": {  "$exists" : True }  })

    fileLinks = []
    for row in rows:
        # db.aierrors.update({
        #     "_id" : row["_id"]
        # }, {
        #     "$set" : {
        #         "is_processed" : True
        #     }
        # })

        fileLinks.append(row["cvimage"]["images"][0])

    return json.dumps(fileLinks, indent=True)

@bp.route("/viz/download/<string:candidate_id>/<int:page>", methods=["GET"])
@check_and_validate_account
def download_viz_file(candidate_id, page):
    ## https://staticrecruitai.excellencetechnologies.in/1993d124dda9e43c6369830e865117fcpdf/page0png/page0.png_viz_.png


    db = initDB(request.account_name, request.account_config)

    row = db.emailStored.find_one({"_id": ObjectId(candidate_id)  })

    db.emailStored.update_one({"_id": ObjectId(candidate_id)  } , {
        '$push' : {
            "cvParsedInfo.debug.training_download" : page
        }
    })

    dest = "/workspace/temp_download"

    filename = str(page) + "---" + row["attachment"][0]["attachment"]["publicFolder"]
    filename = filename + ".png"

    
    

    RESUME_UPLOAD_BUCKET = get_cloud_bucket(request.account_name, request.account_config)

    cloud_url = get_cloud_url(request.account_name, request.account_config)

    bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
    blob = bucket.blob(row["cvimage"]["images"][page].replace(cloud_url,""))

    Path(dest).mkdir(parents=True, exist_ok=True)

    try:
        blob.download_to_filename(os.path.join(dest, filename))
        logger.info("file downloaded at %s", os.path.join(dest, filename))
        return send_from_directory(directory=dest, filename=filename, mimetype='image/webp', as_attachment=True)
    except  Exception as e:
        logger.critical(str(e))
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            "error" : str(e),
            "url" : row["cvimage"]["images"][page]
        })
        # return redirect(row["cvimage"]["images"][page], code=302)





# can we automatically find cv link
# in which there is too much bouding box overlap
# in which the is single big bbox which takes more than 50% of the page
# in which ratio of actual text and ratio of text inside bbox is too much different 

@bp.route('/viz/find_inncorrect_annotation/<string:display_type>', methods=['GET'])
@check_and_validate_account
def find_inncorrect_annotation(display_type = "bbox_json"):
    # avaiable types 
    # bbox_json, bbox_html, text_json, text_html

    db = initDB(request.account_name, request.account_config)

    rows = db.emailStored.find({"cvParsedInfo.debug.jsonOutputbbox": { "$exists" : True}  })

    intersections = {}

    ret = {}
    full_list = []

    for row in rows:

        # if len(intersections) > 5:
        #     continue
        if "training_download" in row["cvParsedInfo"]["debug"]:
            training_download = row["cvParsedInfo"]["debug"]["training_download"]
            logger.info(training_download)
        else:
            training_download = []
            

        if "bbox" in display_type:

            predictions = row["cvParsedInfo"]["debug"]["predictions"]
            
            
            intersections[str(row["_id"])] = {}

            for pred_idx, pred_page in enumerate(predictions):
                instances = pred_page["instances"]
                filename = pred_page["filename"]
                boxes = []
        
                intersections[str(row["_id"])][pred_idx] = {}
                intersections[str(row["_id"])][pred_idx]["filename"] = filename
                intersections[str(row["_id"])][pred_idx]["aurl"] = ""
                intersections[str(row["_id"])][pred_idx]["inter"] = []
                intersections[str(row["_id"])][pred_idx]["training_download"] = 1 if pred_idx in training_download else 0


                for inst in instances:
                    bbox = inst["bbox"]
                    bbox = bbox.replace("[","").replace("]","")
                    bbox = bbox.split(" ")
                    bbox = list(filter(None, bbox))
                    inst["bbox"] = bbox
                    boxes.append(inst)


                for idx, inst in enumerate(boxes):
                    bbox = inst["bbox"]
                    x = float(bbox[0])
                    y = float(bbox[1])
                    width = float(bbox[2])
                    height = float(bbox[3])

                    intersections[str(row["_id"])][pred_idx]["aurl"] = inst["filename"].replace("/workspace/app/detectron/../../cvreconstruction","https://staticrecruitai.excellencetechnologies.in")
                    filename2 = inst["finalfilenamebbox"].replace("/workspace/app/detectron/../../cvreconstruction","https://staticrecruitai.excellencetechnologies.in")

                    obj = {
                        "filename" : filename2,
                        "bbox" : bbox,
                        "inter" : []
                    }
                    for idx2, inst2 in enumerate(boxes):

                        if idx2 != idx:
                            bbox2 = inst2["bbox"]
                            x2 = float(bbox2[0])
                            y2 = float(bbox2[1])
                            width2 = float(bbox2[2])
                            height2 = float(bbox2[3])

                            filename2 = inst2["finalfilenamebbox"].replace("/workspace/app/detectron/../../cvreconstruction","https://staticrecruitai.excellencetechnologies.in")


                            
                            # this condition works but many times bbox are like intersecting on 80% of the area
                            if x2 >= x and y2 >= y and x + width > x2 + width2 and y + height > y2 + height2:
                                obj["inter"].append({
                                    "bbox" : bbox2,
                                    "calc" : [(x2,x), (y2, y), (x+width,x2+width2), (y + height,y2+height2) ],
                                    "url" : filename2
                                })
                            
                            if x2 >= x * .95 and y2 >= y * .95 and (x + width) * 1.05 > x2 + width2 and (y + height) * 1.05 > y2 + height2:
                                x_overlap = max(0, min(x + width, x2 + width2) - max(x, x2))
                                y_overlap = max(0, min(y + height, y2 + height2) - max(y, y2))
                                overlapArea = x_overlap * y_overlap

                                actual_area = width * height2
                                percentage_overlap = overlapArea/actual_area
                                if percentage_overlap > .1:
                                    obj["inter"].append({
                                        "bbox" : bbox2,
                                        "calc" : [(x2,x), (y2, y), (x+width,x2+width2), (y + height,y2+height2) ],
                                        "url" : filename2,
                                        "overlapArea" : overlapArea,
                                        "percentage_overlap" : percentage_overlap
                                        
                                    })


                    if len(obj["inter"]) > 0:
                        intersections[str(row["_id"])][pred_idx]["inter"].append(obj)

        if "text" in display_type:
            jsonOutputbbox = row["cvParsedInfo"]["debug"]["jsonOutputbbox"]
            candidate_ret = []
            for idx, page in enumerate(jsonOutputbbox):
                page_contents = row["cvParsedInfo"]["debug"]["page_contents"]
                page_text = page_contents[idx]
                fullText = []
                for line in page:
                    correctLine = line["correctLine"]
                    fullText.append(correctLine)
                
                page_text_percentage = (len(fullText)) / len(page_text)
                # candidate_ret.append(page_text_percentage)
                page_text = page_text.splitlines()

                nFullText = []
                len_words_full_text = 0

                for line in fullText:
                    words = [w.strip() for w in line.split()]
                    # words = list(set(words))
                    # for w in words:
                    len_words_full_text += len(words)
                    if len(words) > 0:
                        nFullText.append( " ".join(words))

                npage_text = []
                len_words_page_text = 0
                for line in page_text:
                    line = line.strip()
                    is_single_char_line = True
                    for word in line.split():
                        if len(word.strip()) > 1:
                            is_single_char_line = False
                    
                    if is_single_char_line:
                        line = "".join(line.split())

                    words = [w.strip() for w in line.split()]
                    # words = list(set(words))
                    # for w in words:
                    

                    len_words_page_text += len(words)
                    if len(words) > 0:
                        npage_text.append( " ".join(words))

                cvimage = row["cvimage"]["images"][idx]
                filename = cvimage.split("/")[-1]

                cvimage = cvimage.replace(filename, "page" + str(idx) +"png/page" + str(idx) + ".png_viz_.png")
                obj = {
                    "fullText" : nFullText,
                    "page_text" : npage_text,
                    "id": str(row["_id"]),
                    "cv_image" : cvimage,
                    "len_words_page_text" : len_words_page_text,
                    "len_words_full_text" : len_words_full_text,
                    "per" : len_words_full_text / len_words_page_text if len_words_page_text > 0 else 0,
                    "candidate_id" : str(row["_id"]),
                    "page" : idx,
                    "account_name" : request.account_name,
                    "training_download" : 1 if idx in training_download else 0
                }
                candidate_ret.append(obj)
                if obj["per"] > 0:
                    full_list.append(obj)

            ret[str(row["_id"])] = candidate_ret

    
    if display_type == "text_html":
        full_list = sorted(full_list, key=lambda k: k['per'])
        return render_template('table.html', full_list=full_list)
    
    if display_type == "text_json":
        full_list = sorted(full_list, key=lambda k: k['per'])
        return jsonify(full_list)
    

    if "bbox" in display_type:
        foundinter = []
        for mongoid in intersections:
            for page_idx in intersections[mongoid]:
                if len(intersections[mongoid][page_idx]["inter"]) > 0:
                    foundinter.append({
                        "id" : mongoid + "-----" + str(page_idx),
                        "no_of_intersections" : len(intersections[mongoid][page_idx]["inter"]),
                        "cv_page_url" : intersections[mongoid][page_idx]["aurl"],
                        "candidate_id" : mongoid,
                        "page" : page_idx,
                        "account_name" : request.account_name,
                        "training_download" : intersections[mongoid][page_idx]["training_download"]
                    })


        foundinter = sorted(foundinter, key=lambda k: -1 * k['no_of_intersections'])

    if display_type == "bbox_json":
        return jsonify(foundinter)

    if display_type == "bbox_html":
        return render_template('bbox_table.html', foundinter=foundinter)



@bp.route('/viz/convert_for_annotation', methods=['GET'])
@check_and_validate_account
def convert_for_annotation():
    db = initDB(request.account_name, request.account_config)

    rows = db.aierrors.find({
        "error" : "IMAGEVIZ",
        "is_processed" : {
            "$exists" : False
        } 
    })

    fileLinks = []
    for row in rows:
        db.aierrors.update({
            "_id" : row["_id"]
        }, {
            "$set" : {
                "is_processed" : True
            }
        })

        fileLinks.append(row["fileLink"])

    return json.dumps(fileLinks, indent=True)


@bp.route('/get_cv_parts_classify/<int:download>', methods=['GET'])
@check_and_validate_account
def get_cv_parts_classify(download = 0):

    db = initDB(request.account_name, request.account_config)

    rows = db.aierrors.find({"userId":"5ea7a7041b52f0003bfc5554","error":"CVPARTSCLASSIFY"})

    ret = []
    for row in rows:
        label = row["cvParseClassifyLabel"]
        line = row["line"]

        if len(line) > 0:
            ret.append({
                "text" : line,
                "label" : label
            })

    if download == 1:
        content = json.dumps(ret)
        return Response(content, 
                mimetype='application/json',
                headers={'Content-Disposition':'attachment;filename=cvclassify.json'})
    else:
        return jsonify(ret)

@bp.route('/ner/convert_to_label_studio', methods=['GET'])
@check_and_validate_account
def ner_to_label_studio():

    db = initDB(request.account_name, request.account_config)

    rows = db.aierrors.find({
        "error" : "NER",
        "is_processed" : {
            "$exists" : False
        } 
    })

    lines = []
    tags = []

    version_base_path = BASE_PATH + "/../ner/backup/"

    max_version = 0
    for version in os.listdir(version_base_path):
        v = version.replace("v","")
        v = int(v)
        if v > max_version:
            max_version = v

    # max_version = 1

    exist_max_version_path = BASE_PATH + "/../ner/backup/v" + str(max_version)+"/"

    final_json = json.load(open(exist_max_version_path + 'tasks.json'))

    new_max_version_path = BASE_PATH + "/../ner/backup/v" + str(max_version+1)+"/"

    COMPLETION_PATH  = new_max_version_path + "completions/"

    PREDICTION_PATH = new_max_version_path + "predictions/"

    shutil.copytree(exist_max_version_path + "completions", COMPLETION_PATH)

    Path(PREDICTION_PATH).mkdir(parents=True, exist_ok=True)
    
    for row in rows:
        db.aierrors.update({
            "_id" : row["_id"]
        }, {
            "$set" : {
                "is_processed" : True    
            }
            
        })
        if "line" in row and "entity" in row:
            line = row["line"]
            entity = row["entity"]
            isTrue = False

            if "markTrue" in row:
                isTrue = True

            if isTrue:
                result = []

                for tag in entity:
                    res = {
                        "from_name": "ner",
                        "honeypot": True,
                        "id": uuid.uuid4().hex,
                        "source": "$text",
                        "score" : tag["confidence"],
                        "to_name": "text",
                        "type": "labels",
                        "value": {
                            "start": tag["start_pos"],
                            "end": tag["end_pos"],
                            "labels": [
                                tag["type"]
                            ],
                            "text": tag["text"]
                        }
                    }
                    
                    result.append(res)

                completion = {
                    "completions": [{
                        "id": uuid.uuid4().hex,
                        "lead_time": 20,
                        "result": result,
                        "data" : {
                            "text": line
                        },
                        "id": len(final_json),
                        "task_path": "../tasks.json"
                    }]
                }


            
                data = json.dumps(completion, indent=1)
                with open(PREDICTION_PATH + str(len(final_json)) + '.json', 'w') as f:
                    f.write(data)

            obj = {
                "data" : {
                    "text": line,
                    "id": len(final_json)
                }

            }
            final_json[str(len(final_json))] = obj

    
    

    data = json.dumps(final_json, indent=1)
    
    with open(new_max_version_path + 'tasks.json', 'w') as f:
        f.write(data)


    return jsonify({
        "new_max_version_path" : new_max_version_path,
        "count" : len(final_json)
    }), 200
