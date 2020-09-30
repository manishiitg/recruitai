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


def get_es_index(account_name, account_config):
    return account_config["elasticsearch"]["index"]


def get_cloud_bucket(account_name, account_config):
    return account_config["google_cloud"]["bucket"]

def get_cloud_url(account_name, account_config):
    return account_config["google_cloud"]["url"]

import os
import requests
from requests.auth import HTTPBasicAuth

def get_queues():
    amqp_url_base = os.getenv('RABBIT_API_URL')
    RabbitMQLOGIN = os.getenv("RABBIT_LOGIN")
    res = requests.get(amqp_url_base + "/api/queues", verify=False,
                       auth=HTTPBasicAuth(RabbitMQLOGIN.split(":")[0], RabbitMQLOGIN.split(":")[1]))
    queues = res.json()
    # LOGGER(json.dumps(queues, indent=True))

    mq_status = {}
    running_process = 0
    total = 0
    for queue in queues:

        if "consumers" in queue.keys():
            mq_status[queue["name"]] = {
                "consumers": queue["consumers"],
                "in_process": queue["messages_unacknowledged_ram"] + queue["messages_ready"]
            }
            running_process += int(queue["messages_unacknowledged_ram"])
            total += int(queue["messages_unacknowledged_ram"]) + int(queue["messages_ready"])
        else:
            mq_status[queue["name"]]["in_process"] = 0

    mq_status["all"] = {
        "consumers": 0,
        "in_process": total
    }

    return mq_status


import time
def get_resume_priority(timestamp_seconds):
    cur_time = time.time()
    days = 0
    if timestamp_seconds == 0: 
        # manual candidate
        priority = 10
    else:
        days =  abs(cur_time - timestamp_seconds/1000)  / (60 * 60 * 24 )

        if days < 1:
            priority = 9
        elif days < 7:
            priority = 8
        elif days < 30:
            priority = 7
        elif days < 90:
            priority = 6
        elif days < 365:
            priority = 5
        elif days < 365 * 2:
            priority = 4
        else:
            priority = 1
    
    return priority, days, cur_time