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
def init_elastic_search(account_name, account_config):
    if not has_es:
        return None


    global es
    if account_name not in es:
        es[account_name] = Elasticsearch(account_config["elasticsearch"]["host"])

    return es[account_name]


def get_es_index(account_name, account_config):
    return account_config["elasticsearch"]["index"]


def get_cloud_bucket(account_name, account_config):
    return account_config["google_cloud"]["bucket"]

def get_cloud_url(account_name, account_config):
    return account_config["google_cloud"]["url"]