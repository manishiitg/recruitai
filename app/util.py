from app import mongo
from bson.objectid import ObjectId
import requests
#from slackclient import SlackClient


def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc
