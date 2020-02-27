from flask_pymongo import PyMongo
from app.config import MONGO_URI, SEARCH_URL, REDIS_PORT, REDIS_HOST
from elasticsearch import Elasticsearch
import redis

def init_db():
    mongo = PyMongo()
    return mongo


def get_db(app, mongo):
    app.config["MONGO_URI"] = MONGO_URI
    mongo.init_app(app)

es = None
def init_elastic_search():
    global es
    if es is None:
        es = Elasticsearch(SEARCH_URL)
    return es

r = None
def init_redis():
    global r
    if r is None:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    
    return r