from app.logging import logger
from pymongo import MongoClient


import redis

r = redis.Redis(host=os.environ.get("REDIS_HOST","redis"), port=os.environ.get("REDIS_PORT",6379), db=0)
db = None
def initDB():
    global db
    if db is None:
        client = MongoClient(os.environ.get("RECRUIT_BACKEND_DB" , "mongodb://176.9.137.77:27017/hr_recruit_dev"))
        db = client[os.environ.get("RECRUIT_BACKEND_DATABASe" , "hr_recruit_dev")]

    return db



def start(mongoid, filter_type="job_profile"):

    db = initDB()

    if filter_type == "job_profile":
        ret = db.emailStored.find({
            'job_profile_id': mongoid
        })

    elif filter_type == "candidate":
        ret = db.emailStored.find({
            'candidateClassify': 
        })

    pass