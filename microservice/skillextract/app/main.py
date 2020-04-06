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

amqp_url = os.environ.get('RABBIT_DB',"amqp://guest:guest@rabbitmq:5672/%2F?connection_attempts=3&heartbeat=3600")


from app.skillextract.start import start as extractSkill
from app.skillsword2vec.start import loadModel

import time

import threading
import functools
import traceback
import requests
# conn  = None

# threads = []


def thread_task( conn, ch, method_frame, properties, body):
    body = json.loads(body)
    logger.info(body)

    account_name = None
    if "account_name" in body:
        account_name = body["account_name"]
    else:
        LOGGER.critical("no account found. unable to proceed")
        return add_threadsafe_callback(ch, method_frame,properties,'no account found')

    
    account_config = body["account_config"]


    if isinstance(body, dict):
        if "ping" in body:
            time.sleep(5)            
            ret = dict(pong=body["ping"])
            ret = json.dumps(ret)
            add_threadsafe_callback(conn, ch, method_frame,properties,ret)
        elif "action" in body:
            logger.info("message recieved %s" , body)
            if body["action"] == "extractSkill":
                mongoid = body["mongoid"]
                findSkills = body["skills"]
                try:
                    ret = extractSkill(findSkills, mongoid, False, account_name, account_config)
                    ret = json.dumps(ret,default=str)

                    try:
                        if "meta" in body:
                            meta = body["meta"]
                            if "callback_url" in meta:
                                body["extractSkill"] = ret
                                meta["message"] = json.loads(json.dumps(body))
                                requests.post(meta["callback_url"], json=meta)

                    except Exception as e:
                        traceback.print_exc()
                        LOGGER.critical(e)

                        
                except Exception as e:
                    ret = str(e)
                    traceback.print_exc()
                
                logger.info("completed")
                add_threadsafe_callback(conn, ch, method_frame,properties,ret)
            else:
                add_threadsafe_callback(conn, ch, method_frame,properties, 'Action not found')

        else:
            add_threadsafe_callback(conn, ch, method_frame,properties, 'Invalid Object Format')
    
    else:
        add_threadsafe_callback(conn, ch, method_frame,properties,'Internal Error From Clasify')


def add_threadsafe_callback(conn, ch,  method_frame,properties, msg):
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
    t = threading.Thread(target = thread_task, args = (conn, ch, method, properties, body))
    t.start()
    # threads.append(t)
    # logger.info(t.is_alive())
    # no need of thread for now as its very less time taking task
    # thread_task( ch, method, properties, body )
    thrds.append(t)

def main():
    loadModel()
    conn = pika.BlockingConnection(pika.URLParameters(amqp_url))
    ch = conn.channel()

    # ch.exchange_declare(
    #     exchange=EXCHANGE,
    #     exchange_type="direct",
    #     passive=False,
    #     durable=True,
    #     auto_delete=False)

    # declare a queue
    ch.queue_declare(queue=SERVER_QUEUE, auto_delete=True, durable=True) #exclusive=True,
    ch.basic_qos(prefetch_count=10)
    threads = []
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