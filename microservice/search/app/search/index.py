from app.config import IS_DEV
from datetime import datetime
from app.logging import logger
from app import db
import json
from app.config import RESUME_INDEX_NAME

import traceback
import redis
import os

r = redis.StrictRedis(host=os.environ.get("REDIS_HOST","redis"), port=os.environ.get("REDIS_PORT",6379), db=0, decode_responses=True)

indexCreated = False


def getIndex():
    return RESUME_INDEX_NAME

def createIndex():
    global indexCreated 
    if indexCreated:
        return 
    
    indexCreated = True
    es = db.init_elastic_search()
    indexName = getIndex()

    ret = es.indices.create(index=indexName, ignore=400, body={
        "mappings": {
            "properties": {
                "resume": {"type": "text", "analyzer": "standard"}, 
                "extra_data" : { "type" : "object", "enabled" : False }
            }
        }
    })
    logger.info(ret)


def addDoc(mongoid, lines, extra_data={}):
    
    createIndex()
    indexName = getIndex()

    es = db.init_elastic_search()
    ret = es.index(index=indexName, id=mongoid, body={
        "resume": " ".join(lines),
        # "extra_data": json.loads(json.dumps(extra_data, default=str)),
        "extra_data": {},
        "refresh": True,
        "timestamp": datetime.now()})
    logger.info(ret)
    return ret

def addMeta(mongoid, meta):
    indexName = getIndex()

    es = db.init_elastic_search()
    
    
    try:
        ret = es.update(index=indexName, id=mongoid, body={
            "doc" : {
                "extra_data" : {
                    # "meta" : json.loads(json.dumps(extra_data, default=str))
                    "meta" : {}
                }
            }
        })
        logger.info(ret)
    except Exception as e:
        logger.critical(e)
        traceback.print_exception(e)

    return ret


def getDoc(mongoid):
    indexName = getIndex()

    es = db.init_elastic_search()
    return es.get(index=indexName, id=mongoid)


def deleteDoc(mongoid):
    indexName = getIndex()

    es = db.init_elastic_search()
    return es.delete(index=indexName, id=mongoid)


def searchDoc(searchText):
    indexName  = getIndex()

    es = db.init_elastic_search()
    ret = es.search(
        index=indexName,
        body={
            "query":
                {
                    "match":
                    {
                        "resume":  searchText
                    }
                }
        }
    )
    hits = ret["hits"]
    for idx, hit in enumerate(hits["hits"]):
        id = hit["_id"]
        data = r.get(id)
        if not data:
            data = {}
        else:
            data = json.loads(data)

        del ret["hits"]["hits"][idx]["_source"]["extra_data"]

        ret["hits"]["hits"][idx]["_source"]["redis-data"] = data


    return ret


def deleteAll():
    indexName  = getIndex()

    es = db.init_elastic_search()
    return es.delete_by_query(indexName, {
        "query": {
            "match_all": {}
        }
    })


# def flush():
#     if IS_DEV:
#         indexName = "devresume"
#     else:
#         indexName = 'resume'

#     es = db.init_elastic_search()
#     return es.flush(indexName)


# def refresh():
#     if IS_DEV:
#         indexName = "devresume"
#     else:
#         indexName = 'resume'

#     es = db.init_elastic_search()
#     return es.refresh(indexName)
