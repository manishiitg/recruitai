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

from app.filter.start import fetch, indexAll, index, clear_unique_cache, get_candidate_tags, general_api_speed_up, get_index

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
        return add_threadsafe_callback(ch, method_frame,properties,json.dumps("no account found"))

    
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
                if body["starred"]:
                    on_starred = True

            on_is_read = False
            if 'is_read' in body:
                if body["is_read"]:
                    on_is_read = True

            on_is_un_read = False
            if 'is_unread' in body:
                if body["is_unread"]:
                    on_is_un_read = True

            on_conversation = False
            if 'conversation' in body:
                if body["conversation"]: 
                    on_conversation = True

            on_un_parsed = False
            if 'unparsed' in body:
                if body['unparsed']:
                    on_un_parsed = True

            on_highscore = False
            if 'highscore' in body:
                if body['highscore']:
                    on_highscore = True

            on_is_note_added = False
            if 'is_note_added' in body:
                if body['is_note_added']:
                    on_is_note_added = True
            
            on_calling_status = None
            if 'calling_status' in body:
                if body['calling_status']:
                    on_calling_status = body['calling_status']

            filter = {}

            if "filter" in body:
                filter = body["filter"]

            sortby = None
            sortorder = None

            if "sortby" in body:
                sortby = body["sortby"] 
            
            if "sortorder" in body:
                sortorder = body["sortorder"] 

            # job_profile, candidate, full_map
            if action == 'fetch':
                ret = fetch(fetch_id, fetch_type, tags, page, limit, on_ai_data, filter, on_starred, on_conversation, on_highscore, on_un_parsed, on_is_read, on_is_un_read, on_is_note_added, on_calling_status , sortby, sortorder, account_name, account_config)
                # logger.info(ret)
                add_threadsafe_callback(ch, method_frame,properties,ret)
            else:
                add_threadsafe_callback(ch, method_frame,properties, json.dumps({}))
                index(fetch_id, None, fetch_type, account_name, account_config)
                # ret = json.dumps(ret)
        elif body["action"] == "filter_index_get":
            if "job_profile_id" in body:
                ret = get_index(body["tag_id"], body["job_profile_id"], account_name, account_config)
            else:
                ret = get_index(body["tag_id"], None, account_name, account_config)
            add_threadsafe_callback(ch, method_frame,properties, ret)

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

        elif body["action"] == "get_education_display":
            ret = get_education_display(body["degree"], account_name, account_config)
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)

        elif body["action"] == "get_exp_display":
            ret = get_exp_display(account_name, account_config)
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)

        elif "ping" in body:
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