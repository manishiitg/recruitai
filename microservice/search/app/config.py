import os
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

IN_COLAB = False

SEARCH_URL  = os.getenv('ELASTIC_SEARCH_URL',"elasticsearch:9200")

IS_DEV = os.getenv("IS_DEV", "False")
if IS_DEV == "False":
    IS_DEV = False
else:
    IS_DEV = True

if IS_DEV:
    RESUME_INDEX_NAME = os.getenv('RESUME_INDEX_NAME',"devresume")
else:
    RESUME_INDEX_NAME = os.getenv('RESUME_INDEX_NAME',"resume")
