import os 
from google.cloud import storage

SEARCH_URL  = os.getenv('ELASIC_SEARCH_URL', "127.0.0.1:9200")

REDIS_HOST = os.getenv('REDIS_URL', "127.0.0.1")
REDIS_PORT = os.getenv('REDIS_PORT', "6379")

MONGO_URI = os.getenv('RECRUIT_BACKEND_DB', "mongodb://staging_recruit:staging_recruit@5.9.144.226:27017/staging_recruit")

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

RESUME_UPLOAD_BUCKET = os.getenv("CV_BUCKET_URL","staticrecruitai.excellencetechnologies.in")

GOOGLE_BUCKET_URL = "https://" + RESUME_UPLOAD_BUCKET + "/"

storage_client = storage.Client.from_service_account_json(
            BASE_PATH + '/../RecruitAI.json')

try:
  import google.colab
  IN_COLAB = True
except:
  IN_COLAB = False


IS_DEV = os.getenv("IS_DEV", True)
# if true, this will parse cv instantly instead of rq worker