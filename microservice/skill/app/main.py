
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

amqp_url = os.getenv('RABBIT_DB')

from app.skillsword2vec.start import loadModel, loadDomainModel, get_similar, vec_exists, get_start_match, get_domain_list
from app.statspublisher import sendMessage as updateStats

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
            if vec_exists(skill.lower()):
                serializedPositiveSkill.append(skill.lower())

    serializedNegativeSkill = []
    for skill in negative:
        if " " in skill:
            if vec_exists("_".join(skill.lower().split(" "))):
                serializedNegativeSkill.append("_".join(skill.lower().split(" ")))
            else:
                serializedNegativeSkill.extend(skill.lower().split(" "))
        else:
            if vec_exists(skill.lower()):
                serializedNegativeSkill.append(skill.lower())

    logger.info("seralized positive %s and negative %s",
                serializedPositiveSkill, serializedNegativeSkill)
    return serializedPositiveSkill,  serializedNegativeSkill



def thread_task( ch, method_frame, properties, body):
    body = json.loads(body)
    logger.info(body)
    if isinstance(body, dict):
        if 'domain_list' in body:
            ret = get_domain_list()
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)

        elif "match" in body:
            domain = None
            if "domain" in body:
                domain = body["domain"]

            ret = get_start_match(body["text"], domain)
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)

        elif "keyword" in body:
            domain = None
            if "domain" in body:
                domain = body["domain"]

            serializedPositiveSkill,  serializedNegativeSkill = processWord2VecInput(body["keyword"])
            
            try:
                similar = get_similar(serializedPositiveSkill, serializedNegativeSkill, domain)
                logger.info("similar response %s", similar)
                ret = json.dumps(similar)
            except Exception as e:
                ret = str(e)
            

            
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
    # conn.add_callback_threadsafe(
    #     functools.partial(send_result, ch, method_frame,properties, msg)
    # )

    send_result(ch,  method_frame,properties, msg)

def send_result(ch, method_frame,properties, msg):
    ch.basic_publish(exchange=EXCHANGE, routing_key=properties.reply_to, body=msg)
    if ch.is_open:
        ch.basic_ack(method_frame.delivery_tag)

def on_recv_req(ch, method, properties, body):
    # t = threading.Thread(target = functools.partial(thread_task, ch, method, properties, body))
    # t.start()
    # logger.info(t.is_alive())
    # no need of thread for now as its very less time taking task
    thread_task( ch, method, properties, body )

import subprocess
def main():

    result = subprocess.run(['gsutil', '-m', 'cp', '-rn',
                             'gs://general_ai_works/word2vec/', '/workspace/word2vec'], stdout=subprocess.PIPE)

    print(result)

    loadModel()
    loadDomainModel()
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