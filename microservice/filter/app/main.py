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

amqp_url = os.getenv('RABBIT_DB',"amqp://guest:guest@rabbitmq:5672/%2F?connection_attempts=3&heartbeat=3600")

from app.filter.start import fetch, indexAll, index

from app.score.start import get_education_display, get_candidate_score

import time

import threading
import functools

conn  = None


def thread_task( ch, method_frame, properties, body):
    body = json.loads(body)
    logger.info(body)
    if isinstance(body, dict):
        if "fetch" in body:
            fetch_type = body["fetch"]
            fetch_id = body["id"]
            action = body["action"]
            
            # job_profile, candidate, full_map
            if action == 'fetch':
                ret = fetch(fetch_id, fetch_type)
                # logger.info(ret)
                add_threadsafe_callback(ch, method_frame,properties,ret)
            else:
                ret = index(fetch_id, fetch_type)
                ret = json.dumps(ret)
                add_threadsafe_callback(ch, method_frame,properties, ret)
        elif body["action"] == "candidate_score":
            ret = get_candidate_score(body["id"])
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)
        elif body["action"] == "get_education_display":
            ret = get_education_display(body["degree"])
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
    conn.add_callback_threadsafe(
        functools.partial(send_result, ch, method_frame,properties, msg)
    )

def send_result(ch, method_frame,properties, msg):
    ch.basic_publish(exchange=EXCHANGE, routing_key=properties.reply_to, body=msg)
    if ch.is_open:
        ch.basic_ack(method_frame.delivery_tag)

def on_recv_req(ch, method, properties, body):
    logger.info(body)
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
    # ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=SERVER_QUEUE,on_message_callback=on_recv_req)
    ch.start_consuming()



if __name__ == '__main__':
    main()