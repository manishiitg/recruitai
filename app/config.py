import os 
from google.cloud import storage


MONGO_URI = "mongodb://staging_recruit:staging_recruit@5.9.144.226:27017/staging_recruit"

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

RESUME_UPLOAD_BUCKET = "staticrecruitai.excellencetechnologies.in"

GOOGLE_BUCKET_URL = "http://storage.googleapis.com/" + RESUME_UPLOAD_BUCKET + "/"

storage_client = storage.Client.from_service_account_json(
            BASE_PATH + '/../RecruitAI.json')

try:
  import google.colab
  IN_COLAB = True
except:
  IN_COLAB = False