from app.config import IS_DEV
from datetime import datetime
from app.logging import logger
import json
from app.config import RESUME_INDEX_NAME

import traceback
import redis
import os

indexCreated = False

from app.account import get_es_index, init_elastic_search, connect_redis

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
    logger.info(ret)

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
    # logger.info(ret)
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
        logger.info(ret)
    except Exception as e:
        logger.critical(e)
        traceback.print_exception(e)

    return ret

def deleteDoc(mongoid, account_name, account_config):
    indexName = getIndex(account_name, account_config)

    es = init_elastic_search(os.getenv('ELASTIC_USERNAME', 'elastic'), os.getenv('ELASTIC_PASSWORD', 'DkIedPPSCb'),account_name, account_config)
    return es.delete(index=indexName, id=mongoid)


def deleteAll(account_name, account_config):
    indexName  = getIndex(account_name, account_config)

    es = init_elastic_search(os.getenv('ELASTIC_USERNAME', 'elastic'), os.getenv('ELASTIC_PASSWORD', 'DkIedPPSCb'),account_name, account_config)
    return es.delete_by_query(indexName, {
        "query": {
            "match_all": {}
        }
    })