from flask_pymongo import PyMongo
from app.config import MONGO_URI


def init_db():
    mongo = PyMongo()
    return mongo


def get_db(app, mongo):
    app.config["MONGO_URI"] = MONGO_URI
    mongo.init_app(app)