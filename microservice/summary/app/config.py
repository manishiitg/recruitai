import os
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

IN_COLAB = False


import os
from google.cloud import storage

storage_client = storage.Client.from_service_account_json(
            BASE_PATH + '/RecruitAI.json')
