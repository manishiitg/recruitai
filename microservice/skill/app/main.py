
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
SERVER_QUEUE = "rpc.skill.queue"

amqp_url = os.getenv('RABBIT_DB',"amqp://guest:guest@rabbitmq:5672/%2F?connection_attempts=3&heartbeat=3600")

from app.skillsword2vec.start import loadModel, loadGlobalModel, get_similar, vec_exists

import time

import threading
import functools

conn  = None

def processWord2VecInput(keyword):
    if "-" in keyword:
        negative = keyword.split("-")[1]
        positive = keyword.split("-")[0]
    else:
        positive = keyword
        negative = []

    if "+" in positive:
        positive = positive.split("+")
    else:
        positive = [positive]

    serializedPositiveSkill = []
    for skill in positive:
        if " " in skill:
            if vec_exists("_".join(skill.lower().split(" "))):
                serializedPositiveSkill.append("_".join(skill.lower().split(" ")))
            else:
                serializedPositiveSkill.extend(skill.lower().split(" "))
        else:
            serializedPositiveSkill.append(skill.lower())

    serializedNegativeSkill = []
    for skill in negative:
        if " " in skill:
            if vec_exists("_".join(skill.lower().split(" "))):
                serializedNegativeSkill.append("_".join(skill.lower().split(" ")))
            else:
                serializedNegativeSkill.extend(skill.lower().split(" "))
        else:
            serializedNegativeSkill.append(skill.lower())

    logger.info("seralized positive %s and negative %s",
                serializedPositiveSkill, serializedNegativeSkill)
    return serializedPositiveSkill,  serializedNegativeSkill



def thread_task( ch, method_frame, properties, body, is_thread):
    body = json.loads(body)
    logger.info(body)
    if isinstance(body, dict):
        if "keyword" in body:
            if "isGlobal" in body:
                isGlobal = True
            else:
                isGlobal = False

            serializedPositiveSkill,  serializedNegativeSkill = processWord2VecInput(body["keyword"])
            
            similar = get_similar(serializedPositiveSkill, serializedNegativeSkill, isGlobal)

            logger.info("similar response %s", ret)
            ret = json.dumps(ret)
            if is_thread:
                send_result(ch, method_frame,properties, msg)
            else:
                add_threadsafe_callback(ch, method_frame,properties,ret)
            

        elif "ping" in body:
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
        
    
    else:
        if is_thread:
                send_result(ch, method_frame,properties, msg)
        else:
            add_threadsafe_callback(ch, method_frame,properties,'Wrong Input Format For Skill Only Dict')


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

    loadModel()
    # loadGlobalModel()
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