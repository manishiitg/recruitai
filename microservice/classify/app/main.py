
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
from app.statspublisher import sendMessage as updateStats

import time

import threading
import functools

conn  = None


def thread_task( ch, method_frame, properties, body):
    body = json.loads(body)
    if len(body) == 0:
        return add_threadsafe_callback(ch, method_frame,properties,'invalid api call')

    account_name = None
    if "account_name" in body[0]:
        account_name = body[0]["account_name"]
    else:
        LOGGER.critical("no account found. unable to proceed %s", body)
        return add_threadsafe_callback(ch, method_frame,properties,'no account found')

    
    account_config = body[0]["account_config"]


    logger.info(body)
    if isinstance(body, dict):
        if "ping" in body:
            ret = dict(pong=body["ping"])
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)
        else:
            add_threadsafe_callback(ch, method_frame,properties, 'Invalid Object Format')
    if isinstance(body, list):
        ret = classifyData(body)
        logger.info("classify response %s", ret)
        ret = json.dumps(ret)
        add_threadsafe_callback(ch, method_frame,properties,ret)
    else:
        add_threadsafe_callback(ch, method_frame,properties,'Internal Error From Clasify')


def add_threadsafe_callback(ch,  method_frame,properties, msg):
    conn.add_callback_threadsafe(
        functools.partial(send_result, ch, method_frame,properties, msg)
    )

def ack_message(ch, delivery_tag):
    """Note that `ch` must be the same pika channel instance via which
    the message being ACKed was retrieved (AMQP protocol constraint).
    """
    if ch.is_open:
        ch.basic_ack(delivery_tag)
    else:
        # Channel is already closed, so we can't ACK this message;
        # log and/or do something that makes sense for your app in this case.
        pass
    
def send_result(ch, method_frame,properties, msg):
    ch.basic_publish(exchange=EXCHANGE, routing_key=properties.reply_to, body=msg)
    ack_message(ch, method_frame.delivery_tag)

def on_recv_req(ch, method, properties, body):
    logger.info(body)
    # t = threading.Thread(target = functools.partial(thread_task, ch, method, properties, body))
    # t.start()
    # logger.info(t.is_alive())
    # no need of thread for now as its very less time taking task
    thread_task( ch, method, properties, body )

def main():

    test()
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