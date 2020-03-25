import os
from google.cloud import storage
from app.logging import logger

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

RESUME_UPLOAD_BUCKET = os.getenv("CV_BUCKET_URL","staticrecruitai.excellencetechnologies.in")

storage_client = storage.Client.from_service_account_json(
            BASE_PATH + '/RecruitAI.json')

GOOGLE_BUCKET_URL = "https://" + RESUME_UPLOAD_BUCKET + "/"

IN_COLAB = False