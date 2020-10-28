has_mongo = False
try:
    from pymongo import MongoClient
    from bson.objectid import ObjectId
    has_mongo = True   
except ModuleNotFoundError as e:
    pass

db_hosts = {}
def initDB(account_name, account_config):
    if not has_mongo:
        return None
        
    global db_hosts
    if account_name not in db_hosts:
        client = MongoClient(account_config["mongodb"]["host"]) 
        db_hosts[account_name] = client[account_config["mongodb"]["db"]]


    return db_hosts[account_name]


has_redis = False
try:
    import redis 
    has_redis = True   
except ModuleNotFoundError as e:
    pass
    


redis_hosts = {}

def connect_redis(account_name, account_config):
    if not has_redis:
        return None
    global redis_hosts

    if account_name not in redis_hosts:
        redis_hosts[account_name] = redis.StrictRedis(host=account_config["redis"]["host"], port=account_config["redis"]["port"], db=account_config["redis"]["db_index"], decode_responses=True)

    return redis_hosts[account_name]


has_es = False

try:
    from elasticsearch import Elasticsearch
    has_es = True
except Exception as e:
    pass


es = {}
def init_elastic_search(username, password, account_name, account_config):
    if not has_es:
        return None
        
    global es
    if account_name not in es:
        es[account_name] = Elasticsearch(account_config["elasticsearch"]["host"], http_auth=(username, password))

    return es[account_name]


import redis 
from pymemcache.client.base import PooledClient

redis_hosts = {}

def connect_redis(account_name, account_config):
    if "use_cache" not in account_config:
        account_config["use_cache"] = "redis"

    if account_config["use_cache"] == "redis":
        global redis_hosts

        if account_name not in redis_hosts:
            redis_hosts[account_name] = redis.StrictRedis(host=account_config["redis"]["host"], port=account_config["redis"]["port"], db=account_config["redis"]["db_index"], decode_responses=True)

        return redis_hosts[account_name]
    
    elif account_config["use_cache"] == "memcached":
        if account_name not in redis_hosts:
            redis_hosts[account_name] = PooledClient(account_config["memcached"]["host"], max_pool_size=4)
        return redis_hosts[account_name]

from app.logging import logger
def r_exists(key, account_name, account_config):
    account_config["use_cache"] = "memcached"
    key = account_name + "_" + key
    key = key.replace(" ", "")
    r = connect_redis(account_name, account_config)
    if account_config["use_cache"] == "redis":
        return r.exists(key)
    else:
        if r.get(key) is None:
            return False
        else:
            return True

import json
def r_get(key, account_name, account_config):
    account_config["use_cache"] = "memcached"
    r = connect_redis(account_name, account_config)
    key = account_name + "_" + key
    key = key.replace(" ", "")
    ret = r.get(key)
    if not ret:
        ret = json.dumps("")
    return ret


def r_set(key, value, account_name, account_config, ex = None):
    account_config["use_cache"] = "memcached"
    r = connect_redis(account_name, account_config)
    key = account_name + "_" + key 
    key = key.replace(" ", "")
    try:
        if ex:
            if account_config["use_cache"] == "redis":
                r.set(key, value, ex=ex)
            else:
                r.set(key, value, expire=ex)
        else:
            r.set(key , value)
    except Exception as e:
        logger.critical("redis exception")
        logger.critical(e)

def r_scan_iter(account_name, account_config, match=None):
    account_config["use_cache"] = "memcached"
    r = connect_redis(account_name, account_config)
    if account_config["use_cache"] == "redis":
        if match:
            ret = r.scan_iter(match=match)
        else:
            ret = r.scan_iter()
    elif account_config["use_cache"] == "memcached":
        ret = r.stats()
    
    scan = []
    for key in ret:
        if account_name + "_" in str(key):
            scan.append(key)

    return scan

def r_flushdb(account_name, account_config):
    account_config["use_cache"] = "memcached"
    r = connect_redis(account_name, account_config)
    # r.flushdb()
    for key in r_scan_iter(account_name, account_config):
        r.delete(key)

def get_es_index(account_name, account_config):
    return account_config["elasticsearch"]["index"]


def get_cloud_bucket(account_name, account_config):
    return account_config["google_cloud"]["bucket"]

def get_cloud_url(account_name, account_config):
    return account_config["google_cloud"]["url"]