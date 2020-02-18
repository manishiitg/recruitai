from flask_pymongo import PyMongo
from app.config import MONGO_URI, SEARCH_URL
from elasticsearch import Elasticsearch


def init_db():
    mongo = PyMongo()
    return mongo


def get_db(app, mongo):
    app.config["MONGO_URI"] = MONGO_URI
    mongo.init_app(app)

def init_elastic_search():
    es = Elasticsearch(SEARCH_URL)
    return es