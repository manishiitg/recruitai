
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

amqp_url = os.getenv('RABBIT_DB')

from app.search.index import createIndex, addDoc, addMeta, deleteDoc, getDoc, searchDoc, deleteAll, getStats



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
        LOGGER.critical("no account found. unable to proceed")
        add_threadsafe_callback(ch, method_frame,properties,'no account found')
        return

    
    account_config = body["account_config"]

    if isinstance(body, dict):
        if "ping" in body:
            time.sleep(5)            
            ret = dict(pong=body["ping"])
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)
        elif "action" in body:
            action = body["action"]
            ret = {}
            # need to remove add, delete etc from here as using searchindex for that now 
            # if action == "addDoc":
            #     ret = addDoc(body["id"] , body["lines"], body["extra_data"], account_name, account_config)
            #     pass
            # elif action == "addMeta":
            #     ret = addMeta(body["id"] , body["meta"], account_name, account_config)
            #     pass
            # elif action == "deleteDoc":
            #     ret = deleteDoc(body["id"], account_name, account_config)
            # el
            if action == "getDoc":
                ret = getDoc(body["id"], account_name, account_config)
            elif action == "searchDoc":
                ret = searchDoc(body["search"], account_name, account_config)
            elif action == "deleteAll":
                ret = deleteAll(account_name, account_config)   
            elif action == "stats":
                ret = getStats(account_name, account_config)   

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
    if ch.is_open:
        ch.basic_ack(method_frame.delivery_tag)

def on_recv_req(ch, method, properties, body):
    
    logger.info(body)
    # t = threading.Thread(target = functools.partial(thread_task, ch, method, properties, body))
    # t.start()
    # logger.info(t.is_alive())
    thread_task(ch, method, properties, body)

def main():

    
    global conn
    conn = pika.BlockingConnection(pika.URLParameters(amqp_url))
    ch = conn.channel()

    # declare a queue
    ch.queue_declare(queue=SERVER_QUEUE, auto_delete=False, durable=True) #exclusive=True,
    # ch
    # .basic_qos(prefetch_count=1)
    ch.basic_consume(queue=SERVER_QUEUE,on_message_callback=on_recv_req)
    ch.start_consuming()





if __name__ == '__main__':
    
    main()