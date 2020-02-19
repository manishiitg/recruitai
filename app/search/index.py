from app.config import IS_DEV
from datetime import datetime
from app.logging import logger
from app import db
import json


def createIndex():
    es = db.init_elastic_search()
    if IS_DEV:
        indexName = "devresume"
    else:
        indexName = 'resume'

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
    if IS_DEV:
        indexName = "devresume"
    else:
        indexName = 'resume'

    es = db.init_elastic_search()
    ret = es.index(index=indexName, id=mongoid, body={
        "resume": " ".join(lines),
        "extra_data": extra_data,
        "refresh": True,
        "timestamp": datetime.now()})
    logger.info(ret)
    return ret

def addMeta(mongoid, meta):
    if IS_DEV:
        indexName = "devresume"
    else:
        indexName = 'resume'

    es = db.init_elastic_search()
    ret = es.update(index=indexName, id=mongoid, body={
        "doc" : {
            "extra_data" : {
                "meta" : meta
            }
        }
    })
    logger.info(ret)
    return ret


def getDoc(mongoid):
    if IS_DEV:
        indexName = "devresume"
    else:
        indexName = 'resume'

    es = db.init_elastic_search()
    return es.get(index=indexName, id=mongoid)


def deleteDoc(mongoid):
    if IS_DEV:
        indexName = "devresume"
    else:
        indexName = 'resume'

    es = db.init_elastic_search()
    return es.delete(index=indexName, id=mongoid)


def searchDoc(searchText):
    if IS_DEV:
        indexName = "devresume"
    else:
        indexName = 'resume'

    es = db.init_elastic_search()
    return es.search(
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


def deleteAll():
    if IS_DEV:
        indexName = "devresume"
    else:
        indexName = 'resume'

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
