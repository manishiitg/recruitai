
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
SERVER_QUEUE = "rpc.gender.queue"

amqp_url = os.getenv('RABBIT_DB',"amqp://guest:guest@rabbitmq:5672/%2F?connection_attempts=3&heartbeat=3600")

from app.gender.start import classify, loadModel
from app.statspublisher import sendMessage as updateStats


import time

import threading
import functools

conn  = None


def thread_task( ch, method_frame, properties, body):
    body = json.loads(body)
    logger.info(body)
    if isinstance(body, dict):
        if "ping" in body:
            ret = dict(pong=body["ping"])
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)
        elif "name" in body:
            ret = classify(body["name"])
            logger.info("classify response %s", ret)
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)
        else:
            add_threadsafe_callback(ch, method_frame,properties, 'Invalid Object Format')
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

def on_recv_req(ch, method, properties, body, args):
    logger.info(body)
    (conn, thrds) = args
    # t = threading.Thread(target = functools.partial(thread_task, ch, method, properties, body))
    # t.start()
    # logger.info(t.is_alive())
    # no need of thread for now as its very less time taking task
    thread_task( ch, method, properties, body )

def main():

    loadModel()
    global conn
    conn = pika.BlockingConnection(pika.URLParameters(amqp_url))
    ch = conn.channel()

    threads = []
    # declare a queue
    ch.queue_declare(queue=SERVER_QUEUE, auto_delete=False, durable=True) #exclusive=True,
    # ch
    # .basic_qos(prefetch_count=1)
    on_message_callback = functools.partial(on_recv_req, args=(conn, threads))
    ch.basic_consume(queue=SERVER_QUEUE,on_message_callback=on_message_callback)
    try:
        ch.start_consuming()
    except KeyboardInterrupt:
        ch.stop_consuming()
        # for t in threads:
        #     logger.info("waiting for thread to complete")
        #     t.join()

    # Wait for all to complete
    for thread in threads:
        thread.join()

    conn.close()




if __name__ == '__main__':
    
    main()