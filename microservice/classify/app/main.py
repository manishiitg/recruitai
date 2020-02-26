
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

def on_recv_req(ch, method, properties, body):
    logger.info(body)
    body = json.loads(body)
    logger.info(body)
    if isinstance(body, dict):
        if "ping" in body:
            time.sleep(5)            
            ret = dict(pong=body["ping"])
            ret = json.dumps(ret)
            ch.basic_publish(exchange=EXCHANGE, routing_key=properties.reply_to, body=ret)
        else:
            ch.basic_publish(exchange=EXCHANGE, routing_key=properties.reply_to, body='Invalid Object Format')
    if isinstance(body, list):
        ret = classifyData(body)
        logger.info("classify response %s", ret)
        ret = json.dumps(ret)
        ch.basic_publish(exchange=EXCHANGE, routing_key=properties.reply_to, body=ret)
    else:
        ch.basic_publish(exchange=EXCHANGE, routing_key=properties.reply_to, body='Internal Error From Clasify')

def main():

    test()
    conn = pika.BlockingConnection(pika.URLParameters(amqp_url))
    ch = conn.channel()

    # declare a queue
    ch.queue_declare(queue=SERVER_QUEUE, auto_delete=True) #exclusive=True,
    ch.basic_consume(queue=SERVER_QUEUE,on_message_callback=on_recv_req)
    ch.start_consuming()



if __name__ == '__main__':
    
    main()