from app.config import IS_DEV
from datetime import datetime
from app.logging import logger
from app import db
import json
from app.config import RESUME_INDEX_NAME
from bson.objectid import ObjectId
from bson import json_util

import traceback
import redis
import os

indexCreated = False

from app.account import get_es_index, init_elastic_search, connect_redis, initDB, r_set, r_get, r_exists

def getIndex(account_name, account_config):
    return get_es_index(account_name, account_config)

def createIndex(account_name, account_config):
    global indexCreated 
    if indexCreated:
        return 
    
    indexCreated = True
    es = init_elastic_search(os.getenv('ELASTIC_USERNAME', 'elastic'), os.getenv('ELASTIC_PASSWORD', 'DkIedPPSCb'), account_name, account_config)
    indexName = getIndex(account_name, account_config)

    ret = es.indices.create(index=indexName, ignore=400, body={
        "mappings": {
            "properties": {
                "resume": {"type": "text", "analyzer": "standard"}, 
                "extra_data" : { "type" : "object", "enabled" : False }
            }
        }
    })
    logger.critical(ret)

def getStats(account_name, account_config):
    createIndex(account_name, account_config)
    indexName = getIndex(account_name, account_config)

    es = init_elastic_search(os.getenv('ELASTIC_USERNAME', 'elastic'), os.getenv('ELASTIC_PASSWORD', 'DkIedPPSCb'), account_name, account_config)
    return es.indices.stats(index=indexName)

def addDoc(mongoid, lines, extra_data={}, account_name = "", account_config = {}):
    
    createIndex(account_name, account_config)
    indexName = getIndex(account_name, account_config)

    es = init_elastic_search(os.getenv('ELASTIC_USERNAME', 'elastic'), os.getenv('ELASTIC_PASSWORD', 'DkIedPPSCb'), account_name, account_config)
    ret = es.index(index=indexName, id=mongoid, body={
        "resume": " ".join(lines),
        # "extra_data": json.loads(json.dumps(extra_data, default=str)),
        "extra_data": {},
        "refresh": True,
        "timestamp": datetime.now()})
    logger.critical(ret)
    return ret

def addMeta(mongoid, meta, account_name, account_config):
    indexName = getIndex(account_name, account_config)
    es = init_elastic_search(os.getenv('ELASTIC_USERNAME', 'elastic'), os.getenv('ELASTIC_PASSWORD', 'DkIedPPSCb'), account_name, account_config)
    
    
    try:
        ret = es.update(index=indexName, id=mongoid, body={
            "doc" : {
                "extra_data" : {
                    # "meta" : json.loads(json.dumps(extra_data, default=str))
                    "meta" : {}
                }
            }
        })
        logger.critical(ret)
    except Exception as e:
        logger.critical(e)
        traceback.print_exception(e)

    return ret


def getDoc(mongoid, account_name, account_config):
    indexName = getIndex(account_name, account_config)
    es = init_elastic_search(os.getenv('ELASTIC_USERNAME', 'elastic'), os.getenv('ELASTIC_PASSWORD', 'DkIedPPSCb'),account_name, account_config)
    return es.get(index=indexName, id=mongoid)


def deleteDoc(mongoid, account_name, account_config):
    indexName = getIndex(account_name, account_config)

    es = init_elastic_search(os.getenv('ELASTIC_USERNAME', 'elastic'), os.getenv('ELASTIC_PASSWORD', 'DkIedPPSCb'),account_name, account_config)
    return es.delete(index=indexName, id=mongoid)
        
def searchDoc(searchText, account_name, account_config):
    indexName  = getIndex(account_name, account_config)
    r = connect_redis(account_name, account_config)

    es =  init_elastic_search(os.getenv('ELASTIC_USERNAME', 'elastic'), os.getenv('ELASTIC_PASSWORD', 'DkIedPPSCb'),account_name, account_config)
    ret = es.search(
        index=indexName,
        body={
            "from" : 0, "size" : 10,
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
        data = r_get(id, account_name, account_config)

        if len(data) == 0:
            data = None
        
        if data == '""':
            data = None
        
        if not data:
            db = initDB(account_name, account_config)
            data = db.emailStored.find_one({ 
                "_id" : ObjectId(id),
                } , 
                {"body": 0, "cvParsedInfo.debug": 0}
            )
            if data is None:
                data = {}
            else:
                data["_id"] = str(data["_id"])
                r_set(data["_id"]  , json.dumps(data,default=json_util.default), account_name, account_config)
                data = json.loads(json.dumps(data,default=json_util.default))
        else:
            data = json.loads(data)

        if "cvParsedInfo" in data:
            cvParsedInfo = data["cvParsedInfo"]
            if "debug" in cvParsedInfo:
                del cvParsedInfo["debug"]

            data["cvParsedInfo"] = cvParsedInfo

            if "newCompressedStructuredContent" in cvParsedInfo:
                del cvParsedInfo["newCompressedStructuredContent"]
            
        del ret["hits"]["hits"][idx]["_source"]["extra_data"]

        ret["hits"]["hits"][idx]["_source"]["redis-data"] = data


    return ret


def deleteAll(account_name, account_config):
    indexName  = getIndex(account_name, account_config)

    es = init_elastic_search(os.getenv('ELASTIC_USERNAME', 'elastic'), os.getenv('ELASTIC_PASSWORD', 'DkIedPPSCb'),account_name, account_config)
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
