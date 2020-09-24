import functools
import time
from app.logging import logger
import pika
import json
import threading

from datetime import datetime
import os 

EXCHANGE = ""
SERVER_QUEUE = "rpc.filter.queue"

amqp_url = os.getenv('RABBIT_DB')

from app.filter.start import fetch, indexAll, index, clear_unique_cache, get_candidate_tags, general_api_speed_up

from app.score.start import get_education_display, get_candidate_score, get_exp_display, get_candidate_score_bulk
from app.statspublisher import sendMessage as updateStats


import time

import threading
import functools

conn  = None


def thread_task( ch, method_frame, properties, body):
    body = json.loads(body)
    logger.critical(body)

    account_name = None
    if "account_name" in body:
        account_name = body["account_name"]
    else:
        logger.critical("no account found. unable to proceed")
        return add_threadsafe_callback(ch, method_frame,properties,'no account found')

    
    account_config = body["account_config"]

    if isinstance(body, dict):
        if "fetch" in body:
            fetch_type = body["fetch"]
            fetch_id = body["id"]
            action = body["action"]
            if "tags" in body:
                tags = body["tags"]
            else:
                tags = []
            
            page = 0
            if "page" in body:
                page = body["page"]

            limit = 25

            if "limit" in body:
                limit = body["limit"]


            on_ai_data = False
            if "ai" in body:
                on_ai_data = body["ai"]

            on_starred = False

            if 'starred' in body:
                on_starred = body["starred"]

            print("on starred", on_starred)

            filter = {}

            if "filter" in body:
                filter = body["filter"]

            # job_profile, candidate, full_map
            if action == 'fetch':
                ret = fetch(fetch_id, fetch_type, tags, page, limit, on_ai_data, filter, on_starred, account_name, account_config)
                # logger.info(ret)
                add_threadsafe_callback(ch, method_frame,properties,ret)
            else:
                add_threadsafe_callback(ch, method_frame,properties, json.dumps({}))
                index(fetch_id, fetch_type, account_name, account_config)
                # ret = json.dumps(ret)
        elif body["action"] == "speed_up":
            ret = general_api_speed_up(body["url"], body["payload"] , body["access_token"], account_name, account_config)
            add_threadsafe_callback(ch, method_frame,properties, ret)
            
        elif body["action"] == "job_overview":
            ret = syncTagData(body["tag_id"], body["url"], body["access_token"], account_name, account_config)
            add_threadsafe_callback(ch, method_frame,properties, ret)

        elif body["action"] == "get_candidate_tags":
            ret = get_candidate_tags(account_name, account_config)
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties, ret)
        elif body["action"] == "update_unique_cache":   
            ret = clear_unique_cache(body["job_profile_id"], body["tag_id"], account_name, account_config)
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties, ret)
        elif body["action"] == "candidate_score_bulk":
            ret = get_candidate_score_bulk(body["id"], account_name, account_config, body["criteria"])
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties, ret)

        elif body["action"] == "candidate_score":
            
            if "filename" in body:
                updateStats({
                        "action" : "resume_pipeline_update",
                        "resume_unique_key" : body["filename"],
                        "meta" : {
                            "mongoid" : body["mongoid"]
                        },
                        "stage" : {
                            "pipeline" : "candidate_score_start",
                            "priority" : body["priority"] 
                        },
                        "account_name" : account_name,
                        "account_config" : account_config
                    })

            if "criteria" not in body:
                body["criteria"] = None

            ret = get_candidate_score(body["id"], account_name, account_config, body["criteria"])
            ret = json.dumps(ret)

            add_threadsafe_callback(ch, method_frame,properties,ret)

            if "filename" in body:
                updateStats({
                        "action" : "resume_pipeline_update",
                        "resume_unique_key" : body["filename"],
                        "meta" : {
                            "ret" : ret,
                            "mongoid" : body["mongoid"]
                        },
                        "stage" : {
                            "pipeline" : "candidate_score_end",
                            "priority" : body["priority"] 
                        },
                        "account_name" : account_name,
                        "account_config" : account_config
                    })

        elif body["action"] == "get_education_display":
            ret = get_education_display(body["degree"], account_name, account_config)
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)

        elif body["action"] == "get_exp_display":
            ret = get_exp_display(account_name, account_config)
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)

        elif "ping" in body:
            time.sleep(5)            
            ret = dict(pong=body["ping"])
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)
        else:
            add_threadsafe_callback(ch, method_frame,properties, 'Invalid Object Format')
        
    
    else:
        add_threadsafe_callback(ch, method_frame,properties,'Wrong Input Format For Skill Only Dict')


def add_threadsafe_callback(ch,  method_frame,properties, msg):
    print("api completed")
    conn.add_callback_threadsafe(
        functools.partial(send_result, ch, method_frame,properties, msg)
    )

def send_result(ch, method_frame,properties, msg):
    ch.basic_publish(exchange=EXCHANGE, routing_key=properties.reply_to, body=msg)
    if ch.is_open:
        ch.basic_ack(method_frame.delivery_tag)

def on_recv_req(ch, method, properties, body):
    # logger.info(body)
    t = threading.Thread(target = functools.partial(thread_task, ch, method, properties, body))
    t.start()
    # logger.info(t.is_alive())
    # thread_task( ch, method, properties, body )

def main():

    # indexAll()
    global conn
    conn = pika.BlockingConnection(pika.URLParameters(amqp_url))
    ch = conn.channel()

    # declare a queue
    ch.queue_declare(queue=SERVER_QUEUE, auto_delete=False, durable=True) #exclusive=True,
    ch.basic_qos(prefetch_count=10)
    ch.basic_consume(queue=SERVER_QUEUE,on_message_callback=on_recv_req)
    ch.start_consuming()



if __name__ == '__main__':
    main()