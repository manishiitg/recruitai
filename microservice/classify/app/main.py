
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
SERVER_QUEUE = "rpc.classify.queue"

amqp_url = os.getenv('RABBIT_DB',"amqp://guest:guest@rabbitmq:5672/%2F?connection_attempts=3&heartbeat=3600")

from app.emailclassify.start import classifyData, loadModel, loadTokenizer, test

import time

import threading
import functools

conn  = None

def thread_task( ch, method_frame, properties, body, is_thread):
    body = json.loads(body)
    logger.info(body)
    if isinstance(body, dict):
        if "ping" in body:
            time.sleep(5)            
            ret = dict(pong=body["ping"])
            ret = json.dumps(ret)
            if is_thread:
                send_result(ch, method_frame,properties, msg)
            else:
                add_threadsafe_callback(ch, method_frame,properties,ret)
        else:
            if is_thread:
                send_result(ch, method_frame,properties, msg)
            else:
                add_threadsafe_callback(ch, method_frame,properties, 'Invalid Object Format')
    if isinstance(body, list):
        ret = classifyData(body)
        logger.info("classify response %s", ret)
        ret = json.dumps(ret)
        if is_thread:
                send_result(ch, method_frame,properties, msg)
        else:
            add_threadsafe_callback(ch, method_frame,properties,ret)
    else:
        if is_thread:
                send_result(ch, method_frame,properties, msg)
        else:
            add_threadsafe_callback(ch, method_frame,properties,'Internal Error From Clasify')


def add_threadsafe_callback(ch,  method_frame,properties, msg):
    conn.add_callback_threadsafe(
        functools.partial(send_result, ch, method_frame,properties, msg)
    )

def send_result(ch, method_frame,properties, msg):
    ch.basic_publish(exchange=EXCHANGE, routing_key=properties.reply_to, body=msg)

def on_recv_req(ch, method, properties, body):
    logger.info(body)
    # t = threading.Thread(target = functools.partial(thread_task, ch, method, properties, body, True))
    # t.start()
    # logger.info(t.is_alive())
    # no need of thread for now as its very less time taking task
    thread_task( ch, method, properties, body , False )

def main():

    test()
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