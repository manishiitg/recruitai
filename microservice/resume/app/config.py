import os
from google.cloud import storage
from app.logging import logger

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

RESUME_UPLOAD_BUCKET = os.getenv("CV_BUCKET_URL","staticrecruitai.excellencetechnologies.in")

storage_client = storage.Client.from_service_account_json(
            BASE_PATH + '/RecruitAI.json')

GOOGLE_BUCKET_URL = "https://" + RESUME_UPLOAD_BUCKET + "/"

RECRUIT_BACKEND_DB = os.getenv("RECRUIT_BACKEND_DB","mongodb://staging_recruit:staging_recruit@5.9.144.226:27017/staging_recruit")

RECRUIT_BACKEND_DATABASE = os.getenv("RECRUIT_BACKEND_DATABASE","hr_recruit_dev")

IN_COLAB = False