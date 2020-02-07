import os 

MONGO_URI = "mongodb://staging_recruit:staging_recruit@5.9.144.226:27017/staging_recruit"

BASE_PATH = os.path.dirname(os.path.abspath(__file__))


try:
  import google.colab
  IN_COLAB = True
except:
  IN_COLAB = False