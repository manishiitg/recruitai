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

from app.logging import logger
def r_exists(key, account_name, account_config):
    r = connect_redis(account_name, account_config)
    return r.exists(account_name + "_" + key)

def r_get(key, account_name, account_config):
    r = connect_redis(account_name, account_config)
    return r.get(account_name + "_" + key)

def r_set(key, value, account_name, account_config, ex = None):
    r = connect_redis(account_name, account_config)
    try:
        if ex:
            r.set(account_name + "_" + key , value, ex=ex)
        else:
            r.set(account_name + "_" + key , value)
    except Exception as e:
        logger.critical("redis exception")
        logger.critical(e)

def r_scan_iter(account_name, account_config, match=None):
    r = connect_redis(account_name, account_config)
    if match:
        return r.scan_iter(match=match)
    else:
        return r.scan_iter()


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


def get_es_index(account_name, account_config):
    return account_config["elasticsearch"]["index"]


def get_cloud_bucket(account_name, account_config):
    return account_config["google_cloud"]["bucket"]

def get_cloud_url(account_name, account_config):
    return account_config["google_cloud"]["url"]