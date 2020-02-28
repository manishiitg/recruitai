
from app.logging import logger
import pika



import functools
import time
from app.logging import logger as LOGGER
import pika
import json
import threading

from datetime import datetime
import os 

EXCHANGE = ""
SERVER_QUEUE = "rpc.search.queue"

amqp_url = os.getenv('RABBIT_DB',"amqp://guest:guest@rabbitmq:5672/%2F?connection_attempts=3&heartbeat=3600")

from app.search.index import createIndex, addDoc, addMeta, deleteDoc, getDoc, searchDoc, deleteAll

import time

import threading
import functools

conn  = None

def thread_task( ch, method_frame, properties, body):
    body = json.loads(body)
    logger.info(body)
    if isinstance(body, dict):
        if "ping" in body:
            time.sleep(5)            
            ret = dict(pong=body["ping"])
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)
        elif "action" in body:
            action = body["action"]
            ret = {}
            if action == "addDoc":
                ret = addDoc(body["id"] , body["lines"], body["extra_data"])
            elif action == "addMeta":
                ret = addMeta(body["id"] , body["meta"])
            elif action == "deleteDoc":
                ret = deleteDoc(body["id"])
            elif action == "getDoc":
                ret = getDoc(body["id"])
            elif action == "searchDoc":
                ret = searchDoc(body["search"])
            elif action == "deleteAll":
                ret = deleteAll()

            logger.info(ret)
            ret = json.dumps(ret)

            add_threadsafe_callback(ch, method_frame,properties, ret)

        else:
            add_threadsafe_callback(ch, method_frame,properties, 'Invalid Object Format')
    
    else:
        add_threadsafe_callback(ch, method_frame,properties,'Internal Error From Search')


def add_threadsafe_callback(ch,  method_frame,properties, msg):
    conn.add_callback_threadsafe(
        functools.partial(send_result, ch, method_frame,properties, msg)
    )

def send_result(ch, method_frame,properties, msg):
    ch.basic_publish(exchange=EXCHANGE, routing_key=properties.reply_to, body=msg)

def on_recv_req(ch, method, properties, body):
    logger.info(body)
    # t = threading.Thread(target = functools.partial(thread_task, ch, method, properties, body))
    # t.start()
    # logger.info(t.is_alive())
    # no need of thread for now as its very less time taking task
    thread_task( ch, method, properties, body  )

def main():

    createIndex()
    global conn
    conn = pika.BlockingConnection(pika.URLParameters(amqp_url))
    ch = conn.channel()

    # declare a queue
    ch.queue_declare(queue=SERVER_QUEUE, auto_delete=True) #exclusive=True,
    # ch
    # .basic_qos(prefetch_count=1)
    ch.basic_consume(queue=SERVER_QUEUE,on_message_callback=on_recv_req)
    ch.start_consuming()



if __name__ == '__main__':
    
    main()