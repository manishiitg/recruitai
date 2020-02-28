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
SERVER_QUEUE = "rpc.skillextract.queue"

amqp_url = os.getenv('RABBIT_DB',"amqp://guest:guest@rabbitmq:5672/%2F?connection_attempts=3&heartbeat=3600")

from app.skillextract.start import start as extractSkill
from app.skillsword2vec.start import loadModel

import time

import threading
import functools
import traceback

conn  = None

# threads = []


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
            if body["action"] == "extractSkill":
                mongoid = body["mongoid"]
                findSkills = body["skills"]
                try:
                    ret = extractSkill(findSkills, mongoid)
                    ret = json.dumps(ret,default=str)
                except Exception as e:
                    ret = str(e)
                    traceback.print_exc()
                
                add_threadsafe_callback(ch, method_frame,properties,ret)
            else:
                add_threadsafe_callback(ch, method_frame,properties, 'Action not found')

        else:
            add_threadsafe_callback(ch, method_frame,properties, 'Invalid Object Format')
    
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
    t = threading.Thread(target = thread_task, args = (ch, method, properties, body))
    t.start()
    # threads.append(t)
    logger.info(t.is_alive())
    # no need of thread for now as its very less time taking task
    # thread_task( ch, method, properties, body )

def main():
    loadModel()
    global conn
    conn = pika.BlockingConnection(pika.URLParameters(amqp_url))
    ch = conn.channel()

    # declare a queue
    ch.queue_declare(queue=SERVER_QUEUE, auto_delete=True) #exclusive=True,
    ch.basic_qos(prefetch_count=5)
    ch.basic_consume(queue=SERVER_QUEUE,on_message_callback=on_recv_req)
    
    ch.start_consuming()
        # for t in threads:
        #     logger.info("waiting for thread to complete")
        #     t.join()

        




if __name__ == '__main__':
    main()