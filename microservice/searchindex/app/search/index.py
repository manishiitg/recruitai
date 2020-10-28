from app.config import IS_DEV
from datetime import datetime
from app.logging import logger
import json
from app.config import RESUME_INDEX_NAME

import traceback
import redis
import os
import hashlib

indexCreated = {}

from app.account import get_es_index, init_elastic_search, connect_redis

def getIndex(account_name, account_config):
    return get_es_index(account_name, account_config)

def createIndex(account_name, account_config):
    global indexCreated 
    if account_name in indexCreated:
        return 
    
    indexCreated[account_name] = True
    es = init_elastic_search(os.getenv('ELASTIC_USERNAME'), os.getenv('ELASTIC_PASSWORD'), account_name, account_config)
    indexName = getIndex(account_name, account_config)

    ret = es.indices.create(index=indexName, ignore=400, body={
        "mappings": {
            "properties": {
                "resume": {"type": "text", "analyzer": "standard"}, 
                "extra_data" : { "type" : "object", "enabled" : False }
            }
        }
    })
    logger.info(ret)

def getDoc(mongoid, account_name, account_config):
    indexName = getIndex(account_name, account_config)
    es = init_elastic_search(os.getenv('ELASTIC_USERNAME'), os.getenv('ELASTIC_PASSWORD'),account_name, account_config)
    return es.get(index=indexName, id=mongoid)

def addDoc(mongoid, lines, extra_data={}, account_name = "", account_config = {}):

    createIndex(account_name, account_config)
    indexName = getIndex(account_name, account_config)

    es = init_elastic_search(os.getenv('ELASTIC_USERNAME'), os.getenv('ELASTIC_PASSWORD'), account_name, account_config)
    
    newlines = " ".join(filter(None, lines))
    addtoindex = False
    try:
        doc = getDoc(mongoid, account_name, account_config)
        # print("++++++++++++++++++")
        # print(doc["_source"]["resume"])
        oldlines = doc["_source"]["resume"]
        

        old_hash = hashlib.md5(oldlines.encode('utf-8')).hexdigest()
        new_hash = hashlib.md5(newlines.encode('utf-8')).hexdigest()

        # print(old_hash, "xxx", new_hash)
        if old_hash != new_hash:
            addtoindex = True

    except Exception as e:
        # es.exceptions.NotFoundError
        addtoindex = True



    if addtoindex:
        ret = es.index(index=indexName, id=mongoid, body={
            "resume": newlines,
            # "extra_data": json.loads(json.dumps(extra_data, default=str)),
            "extra_data": {},
            "refresh": True,
            "timestamp": datetime.now()})
    else:
        logger.critical("index skipped")
        ret = 1
    
    return ret

def addMeta(mongoid, meta, account_name, account_config):
    indexName = getIndex(account_name, account_config)
    es = init_elastic_search(os.getenv('ELASTIC_USERNAME'), os.getenv('ELASTIC_PASSWORD'), account_name, account_config)
    
    
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

def deleteDoc(mongoid, account_name, account_config):
    indexName = getIndex(account_name, account_config)

    es = init_elastic_search(os.getenv('ELASTIC_USERNAME'), os.getenv('ELASTIC_PASSWORD'),account_name, account_config)
    return es.delete(index=indexName, id=mongoid)


def deleteAll(account_name, account_config):
    indexName  = getIndex(account_name, account_config)

    es = init_elastic_search(os.getenv('ELASTIC_USERNAME'), os.getenv('ELASTIC_PASSWORD'),account_name, account_config)
    return es.delete_by_query(indexName, {
        "query": {
            "match_all": {}
        }
    })