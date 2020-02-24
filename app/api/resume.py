from app.picture.start import processAPI as extractPicture
from app.config import storage_client
from app.nerclassify.start import process as classifyNer
from app.ner.start import processAPI as extractNer
from app.detectron.start import processAPI
import json
import os
from pathlib import Path
from app.config import RESUME_UPLOAD_BUCKET, BASE_PATH, GOOGLE_BUCKET_URL, IS_DEV
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

from rq import get_current_job

import subprocess

from app.resumeutil import fullResumeParsing

bp = Blueprint('resume', __name__, url_prefix='/resume')


@bp.route('/getCurrentJob', methods=['GET'])
def getCurrentJob():
    job = get_current_job()
    return jsonify({
        "status": job.get_status(),
        "id": job.id
    })


@bp.route('/emptyQueue', methods=['GET'])
def emptyQueue():
    q.empty()
    return jsonify({})


@bp.route('/getJobStatus/<string:jobId>', methods=['GET'])
def getJobStatus(jobId):
    job = Job.fetch(jobId, connection=redis_conn)
    return jsonify({
        "status": job.get_status(),
        "result": job.result
    })



# @bp.route('/instant/<string:filename>/<string:mongoid>', methods=['GET'])
# def fullparsinginstant(filename, mongoid):
#     return jsonify(fullResumeParsing(filename, mongoid)), 200



@bp.route('/<string:filename>/<string:mongoid>', methods=['GET'])
def fullparsing(filename, mongoid = None):
    logger.info("is dev %s", IS_DEV)
    if IS_DEV:
        logger.info("imedite processing")
        return jsonify(fullResumeParsing(filename, mongoid)), 200
    else:
        logger.info("rq worker")
        job = q.enqueue(fullResumeParsing, filename, mongoid, result_ttl=86400, timeout=500)  # 1 day
        logger.info(job)
        return jsonify(job.id), 200



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
