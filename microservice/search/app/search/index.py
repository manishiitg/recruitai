from app.config import IS_DEV
from datetime import datetime
from app.logging import logger
from app import db
import json
from app.config import RESUME_INDEX_NAME

import traceback


indexCreated = False

def createIndex():
    global indexCreated 
    if indexCreated:
        return 
    
    indexCreated = True
    es = db.init_elastic_search()
    indexName = RESUME_INDEX_NAME

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
    
    
    try:
        ret = es.update(index=indexName, id=mongoid, body={
            "doc" : {
                "extra_data" : {
                    "meta" : meta
                }
            }
        })
        logger.info(ret)
    except es.exceptions.NotFoundError as e:
        logger.critical(e)
        traceback.print_exception(e)

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
