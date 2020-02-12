from app.picture.start import processAPI as extractPicture
from app.config import storage_client
from app.nerclassify.start import process as classifyNer
from app.ner.start import processAPI as extractNer
from app.detectron.start import processAPI
import json
import os
from pathlib import Path
from app.config import RESUME_UPLOAD_BUCKET, BASE_PATH, GOOGLE_BUCKET_URL
from app.logging import logger
from app import token
from app import mongo
from flask import (
    Blueprint, flash, jsonify, abort, request
)

from bson.objectid import ObjectId
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)

from app.queue import q, redis_conn
from rq.job import Job


bp = Blueprint('resume', __name__, url_prefix='/resume')


@bp.route('/testnerclassify', methods=['GET'])
def testnerclassify():
    ret = mongo.db.cvparsingsample.find({"file": "102.pdf"})

    baseURL = GOOGLE_BUCKET_URL

    data = []
    for row in ret:
        data.append(row)

    combinData = classifyNer(data, True)[0]

    newCompressedStructuredContent = {}

    for pageno in combinData["compressedStructuredContent"].keys():
        pagerows = combinData["compressedStructuredContent"][pageno]
        newCompressedStructuredContent[pageno] = []
        for row in pagerows:
            if "classify" in row:
                # classify = row["classify"]
                # if "append" in row:
                #     del row["append"]
                if "finalClaimedIdx" in row:
                    del row["finalClaimedIdx"]
                if "isboxfound" in row:
                    del row["isboxfound"]
                if "lineIdx" in row:
                    del row["lineIdx"]
                if "matchedRow" in row:
                    if "bbox" in row["matchedRow"]:
                        del row["matchedRow"]["bbox"]
                    if "imagesize" in row["matchedRow"]:
                        del row["matchedRow"]["imagesize"]
                    if "matchRatio" in row["matchedRow"]:
                        del row["matchedRow"]["matchRatio"]

                    row["matchedRow"]["bucketurl"] = row["matchedRow"]["filename"].replace(
                        "cvreconstruction/finalpdf", baseURL)

                if "append" in row:
                    newAppend = []
                    for r in row["append"]:
                        if "row" in r:
                            if "finalClaimedIdx" in r["row"]:
                                del r["row"]["finalClaimedIdx"]
                            if "isboxfound" in r["row"]:
                                del r["row"]["isboxfound"]
                            if "lineIdx" in r["row"]:
                                del r["row"]["lineIdx"]
                            if "matchedRow" in r["row"]:
                                if "bbox" in r["row"]["matchedRow"]:
                                    del r["row"]["matchedRow"]["bbox"]
                                if "idx" in r["row"]["matchedRow"]:
                                    del r["row"]["matchedRow"]["idx"]
                                if "isClaimed" in r["row"]["matchedRow"]:
                                    del r["row"]["matchedRow"]["isClaimed"]
                                if "imagesize" in r["row"]["matchedRow"]:
                                    del r["row"]["matchedRow"]["imagesize"]
                                if "matchRatio" in r["row"]["matchedRow"]:
                                    del r["row"]["matchedRow"]["matchRatio"]

                            if "matchedRow" in r["row"]:
                                r["row"]["matchedRow"]["bucketurl"] = r["row"]["matchedRow"]["filename"].replace(
                                    "cvreconstruction/finalpdf", baseURL)

                        newAppend.append(r)

                    row["append"] = newAppend

                newCompressedStructuredContent[pageno].append(row)

    combinData["newCompressedStructuredContent"] = newCompressedStructuredContent

    return jsonify({
        "newCompressedStructuredContent": newCompressedStructuredContent,
        "finalEntity": combinData["finalEntity"],
        "debug": {
            "extractEntity": combinData["extractEntity"],
            "compressedStructuredContent": combinData["compressedStructuredContent"]
        }
    }), 200


@bp.route('/getJobStatus/<string:jobId>', methods=['GET'])
def getJobStatus(jobId):
    job = Job.fetch(jobId, connection=redis_conn)
    return jsonify({
        "status": job.get_status(),
        "result": job.result
    })


def fullResumeParsing(filename):
    bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
    blob = bucket.blob(filename)
    dest = BASE_PATH + "/../temp"
    Path(dest).mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(os.path.join(dest, filename))

    fullResponse = {}

    response, basedir = extractPicture(os.path.join(dest, filename))

    fullResponse["picture"] = {"response": response, "basePath": basedir}

    response, basePath = processAPI(os.path.join(dest, filename))

    # fullResponse["compressedContent"] = {"response" : response, "basePath" : basePath}

    nertoparse = []
    row = []
    for page in response:
        row.append(page["compressedStructuredContent"])

    nertoparse.append({"compressedStructuredContent": row})

    nerExtracted = extractNer(nertoparse)

    # fullResponse["nerExtracted"] = nerExtracted

    row = {}
    row["file"] = filename
    row["nerparsed"] = nerExtracted
    row["compressedStructuredContent"] = {}
    for pageIdx, page in enumerate(response):
        row["compressedStructuredContent"][str(
            pageIdx + 1)] = page["compressedStructuredContent"]

    combinData = classifyNer([row])[0]

    newCompressedStructuredContent = {}

    baseURL = GOOGLE_BUCKET_URL

    for pageno in combinData["compressedStructuredContent"].keys():
        pagerows = combinData["compressedStructuredContent"][pageno]
        newCompressedStructuredContent[pageno] = []
        for row in pagerows:
            if "classify" in row:
                # classify = row["classify"]
                # if "append" in row:
                #     del row["append"]
                if "finalClaimedIdx" in row:
                    del row["finalClaimedIdx"]
                if "isboxfound" in row:
                    del row["isboxfound"]
                if "lineIdx" in row:
                    del row["lineIdx"]
                if "matchedRow" in row:
                    if "bbox" in row["matchedRow"]:
                        del row["matchedRow"]["bbox"]
                    if "imagesize" in row["matchedRow"]:
                        del row["matchedRow"]["imagesize"]
                    if "matchRatio" in row["matchedRow"]:
                        del row["matchedRow"]["matchRatio"]

                    row["matchedRow"]["bucketurl"] = row["matchedRow"]["filename"].replace(
                        "cvreconstruction/finalpdf", baseURL)

                if "append" in row:
                    newAppend = []
                    for r in row["append"]:
                        if "row" in r:
                            if "finalClaimedIdx" in r["row"]:
                                del r["row"]["finalClaimedIdx"]
                            if "isboxfound" in r["row"]:
                                del r["row"]["isboxfound"]
                            if "lineIdx" in r["row"]:
                                del r["row"]["lineIdx"]
                            if "matchedRow" in r["row"]:
                                if "bbox" in r["row"]["matchedRow"]:
                                    del r["row"]["matchedRow"]["bbox"]
                                if "idx" in r["row"]["matchedRow"]:
                                    del r["row"]["matchedRow"]["idx"]
                                if "isClaimed" in r["row"]["matchedRow"]:
                                    del r["row"]["matchedRow"]["isClaimed"]
                                if "imagesize" in r["row"]["matchedRow"]:
                                    del r["row"]["matchedRow"]["imagesize"]
                                if "matchRatio" in r["row"]["matchedRow"]:
                                    del r["row"]["matchedRow"]["matchRatio"]

                            if "matchedRow" in r["row"]:
                                r["row"]["matchedRow"]["bucketurl"] = r["row"]["matchedRow"]["filename"].replace(
                                    "cvreconstruction/finalpdf", baseURL)

                        newAppend.append(r)

                    row["append"] = newAppend

                newCompressedStructuredContent[pageno].append(row)

    combinData["newCompressedStructuredContent"] = newCompressedStructuredContent

    logger.info("full resume parsing completed %s", filename)
    return {
        "newCompressedStructuredContent": newCompressedStructuredContent,
        "finalEntity": combinData["finalEntity"],
        "debug": {
            "extractEntity": combinData["extractEntity"],
            "compressedStructuredContent": combinData["compressedStructuredContent"]
        }
    }


@bp.route('/<string:filename>', methods=['GET'])
def fullparsing(filename):   
    job = q.enqueue(fullResumeParsing, filename)
    logger.info(job)
    return jsonify(job.id), 200

@bp.route('/instant/<string:filename>', methods=['GET'])
def fullparsinginstant(filename):   
    return jsonify(fullResumeParsing(filename)), 200

# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
@bp.route('/picture/<string:filename>', methods=['GET'])
def picture(filename):

    # try:

    bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
    blob = bucket.blob(filename)
    dest = BASE_PATH + "/../temp"
    Path(dest).mkdir(parents=True, exist_ok=True)
    blob.download_to_filename(os.path.join(dest, filename))

    response, basedir = extractPicture(os.path.join(dest, filename))

    return jsonify(response, basedir), 200
    # except Exception as e:
    #     return jsonify(str(e)) , 500


# @bp.route('', methods=['POST', 'GET'])
# @jwt_required
# @token.admin_required
@bp.route('/parse/<string:filename>', methods=['GET'])
def parse(filename):

    try:

        bucket = storage_client.bucket(RESUME_UPLOAD_BUCKET)
        blob = bucket.blob(filename)
        dest = BASE_PATH + "/../temp"
        Path(dest).mkdir(parents=True, exist_ok=True)
        blob.download_to_filename(os.path.join(dest, filename))

        response, basePath = processAPI(os.path.join(dest, filename))

        return jsonify({
            "basePath": basePath,
            "response": response
        }), 200
    except Exception as e:
        return jsonify(str(e)), 500
