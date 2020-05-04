import os 
from app.logging import logger

from google.cloud import storage

BATCH_PROCESSING_DELAY = os.getenv("BATCH_PROCESSING_DELAY", "60")
BATCH_PROCESSING_DELAY = int(BATCH_PROCESSING_DELAY)


BASE_PATH = os.path.dirname(os.path.abspath(__file__))

IN_COLAB = False


IS_DEV = os.getenv("IS_DEV", "False")
if IS_DEV == "False":
    IS_DEV = False
else:
    IS_DEV = True

# if true, this will parse cv instantly instead of rq worker
logger.info("is dev? %s",IS_DEV)

storage_client = storage.Client.from_service_account_json('/workspace/RecruitAI.json')