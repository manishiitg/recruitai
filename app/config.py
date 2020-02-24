import os 
from google.cloud import storage
from app.logging import logger


logger.info(os.environ)

SEARCH_URL  = os.getenv('ELASTIC_SEARCH_URL',"elasticsearch:9200")

REDIS_HOST = os.getenv('REDIS_DB',"redis")
REDIS_PORT = os.getenv('REDIS_PORT',"6379")



MONGO_URI = os.getenv('RECRUIT_BACKEND_DB', "mongodb://staging_recruit:staging_recruit@5.9.144.226:27017/staging_recruit")

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

RESUME_UPLOAD_BUCKET = os.getenv("CV_BUCKET_URL","staticrecruitai.excellencetechnologies.in")

GOOGLE_BUCKET_URL = "https://" + RESUME_UPLOAD_BUCKET + "/"

storage_client = storage.Client.from_service_account_json(
            BASE_PATH + '/../RecruitAI.json')

IN_COLAB = False


IS_DEV = os.getenv("IS_DEV", "False")
if IS_DEV == "False":
    IS_DEV = False
else:
    IS_DEV = True

if IS_DEV:
    RESUME_INDEX_NAME = os.getenv('RESUME_INDEX_NAME',"devresume")
else:
    RESUME_INDEX_NAME = os.getenv('RESUME_INDEX_NAME',"resume")

# if true, this will parse cv instantly instead of rq worker
logger.info("is dev? %s",IS_DEV)