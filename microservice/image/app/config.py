import os
from google.cloud import storage
from app.logging import logger

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

storage_client = storage.Client.from_service_account_json(
            BASE_PATH + '/RecruitAI.json')

IN_COLAB = False