
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
SERVER_QUEUE = "rpc.statsdata.queue"

amqp_url = os.getenv('RABBIT_DB')

from app.stats.index import ai_queue_count, current_candidate_status, get_resume_parsed_per_day, get_resume_parsed_per_week, get_resume_parsed_per_month, resume_parsing_speed_analysis, resume_analytics_single_candidate, resume_only_parsing_speed



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
            ret = dict(pong=body["ping"])
            ret = json.dumps(ret)
            add_threadsafe_callback(ch, method_frame,properties,ret)
        elif "action" in body:
            action = body["action"]
            ret = {}
            
            if action == "queue_count":
                ret = ai_queue_count(account_name, account_config)
            elif action == "current_candidate_status":
                ret = current_candidate_status(body["id"], account_name, account_config)
            elif action == "get_resume_parsed_per_day":
                ret = get_resume_parsed_per_day(account_name, account_config)
            elif action == "get_resume_parsed_per_week":
                ret = get_resume_parsed_per_week(account_name, account_config)
            elif action == "get_resume_parsed_per_month":
                ret = get_resume_parsed_per_month(account_name, account_config)
            elif action == "resume_parsing_speed_analysis":
                ret = resume_parsing_speed_analysis(account_name, account_config)
            elif action == "current_candidate_status_indepth":
                ret = resume_analytics_single_candidate(body['id'], account_name, account_config)
            elif action == "resume_only_parsing_speed":
                ret = resume_only_parsing_speed(account_name, account_config)

            # logger.critical(ret)
            ret = json.dumps(ret, default=str)

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

    try:
        global conn
        conn = pika.BlockingConnection(pika.URLParameters(amqp_url))
        ch = conn.channel()

        # declare a queue
        ch.queue_declare(queue=SERVER_QUEUE, auto_delete=False, durable=True) #exclusive=True,
        # ch
        # .basic_qos(prefetch_count=1)
        ch.basic_consume(queue=SERVER_QUEUE,on_message_callback=on_recv_req)
        ch.start_consuming()
    except Exception as e:
        logger.critical("error")
        logger.critical(e)
        # after some time pika.exceptions.IncompatibleProtocolError: StreamLostError: ("Stream connection lost: ConnectionResetError(104, 'Connection reset by peer')",)
        # this error comes
        time.sleep(60)
        main()

    





if __name__ == '__main__':
    
    main()