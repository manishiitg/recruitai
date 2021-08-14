has_mongo = False
try:
    from pymongo import MongoClient
    from bson.objectid import ObjectId
    has_mongo = True   
except ModuleNotFoundError as e:
    pass

import os

db_hosts = {}
def initDB(account_name, account_config):
    if not has_mongo:
        return None
        
    global db_hosts
    if account_name not in db_hosts:
        account_json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "account.config.json")
        if os.path.exists(account_json_path):
            with open(account_json_path) as ff:
                account_config = json.load(ff)
                if account_name in account_config:
                    account_config = account_config[account_name]
                    logger.info("overwriteing account info", account_config)


        client = MongoClient(account_config["mongodb"]["host"]) 
        db_hosts[account_name] = client[account_config["mongodb"]["db"]]


    return db_hosts[account_name]

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
memcached_hosts = {}

def connect_redis(account_name, account_config):
    
    if account_config["usecache"] == "redis":
        global redis_hosts

        if account_name not in redis_hosts:
            redis_hosts[account_name] = redis.StrictRedis(host=account_config["redis"]["host"], port=account_config["redis"]["port"], db=account_config["redis"]["db_index"], decode_responses=True)

        return redis_hosts[account_name]
    
    elif account_config["usecache"] == "memcached":
        # if account_name not in memcached_hosts:
        #     memcached_hosts[account_name] = PooledClient(account_config["memcached"]["host"], max_pool_size=4)
        # from pymemcache.client.base import Client
        # return Client(account_config["memcached"]["host"])
        return PooledClient(account_config["memcached"]["host"], max_pool_size=4)

from app.logging import logger
def r_exists(key, account_name, account_config):
    key = account_name + "_" + key
    key = key.replace(" ", "")
    r = connect_redis(account_name, account_config)

    if account_config["usecache"] == "redis":
        ret = r.exists(key)
    else:
        if r.get(key) is None:
            ret = False
        else:
            ret = True

    if account_config["usecache"] == "memcached":
        r.close()
    
    return ret

import json
def r_get(key, account_name, account_config):
    r = connect_redis(account_name, account_config)
    key = account_name + "_" + key
    key = key.replace(" ", "")
    ret = r.get(key)
    if not ret:
        ret = json.dumps("")
        
    if account_config["usecache"] == "memcached":
        r.close()

    return ret

def r_set(key, value, account_name, account_config, ex = None):
    r = connect_redis(account_name, account_config)
    key = account_name + "_" + key 
    key = key.replace(" ", "")
    try:
        if ex:
            if account_config["usecache"] == "redis":
                r.set(key, value, ex=ex)
            else:
                r.set(key, value, expire=ex)
        else:
            if account_config['usecache'] == "redis":
                r.set(key , value)
            else:
                ret = r.set(key, value)
    except Exception as e:
        logger.critical("redis exception")
        logger.critical(e)

    if account_config["usecache"] == "memcached":
        r.close()

def r_scan_iter(account_name, account_config, match=None):
    r = connect_redis(account_name, account_config)
    if account_config["usecache"] == "redis":
        if match:
            ret = r.scan_iter(match=match)
        else:
            ret = r.scan_iter()
    elif account_config["usecache"] == "memcached":
        # ret = r.stats("items")
        ret = []
    
    scan = []
    for key in ret:
        if account_name + "_" in str(key):
            scan.append(key)

    if account_config["usecache"] == "memcached":
        r.close()

    return scan

def r_flushdb(account_name, account_config):
    r = connect_redis(account_name, account_config)
    # r.flushdb()
    if account_config["usecache"] == "redis":
        for key in r_scan_iter(account_name, account_config):
            r.delete(key)

    if account_config["usecache"] == "memcached":
        r.close()


def get_es_index(account_name, account_config):
    return account_config["elasticsearch"]["index"]


def get_cloud_bucket(account_name, account_config):
    return account_config["google_cloud"]["bucket"]

def get_cloud_url(account_name, account_config):
    return account_config["google_cloud"]["url"]