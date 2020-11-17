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

amqp_url = os.environ.get('RABBIT_DB')


from app.skillextract.start import start as extractSkill, get_job_criteria
from app.skillsword2vec.start import loadModel, loadDomainModel
from app.statspublisher import sendMessage as updateStats

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
        return add_threadsafe_callback(conn, ch, method_frame,properties,'no account found')

    
    account_config = body["account_config"]


    if isinstance(body, dict):
        if "ping" in body:
            ret = dict(pong=body["ping"])
            ret = json.dumps(ret)
            add_threadsafe_callback(conn, ch, method_frame,properties,ret)
        elif "action" in body:
            logger.critical("message recieved %s" , body)
            if body["action"] == "extractSkill":
                mongoid = body["mongoid"]
                findSkills = body["skills"]
                try:
                    if "filename" in body:
                        updateStats({
                            "action" : "resume_pipeline_update",
                            "resume_unique_key" : body["filename"],
                            "meta" : {
                                "mongoid" : body["mongoid"]
                            },
                            "stage" : {
                                "pipeline" : "skill_extract_start",
                            },
                            "account_name" : account_name,
                            "account_config" : account_config
                        })

                    

                    if findSkills is None:
                        findSkills = []

                    findSkills = list(filter(len, findSkills))

                    logger.critical("find skills %s", findSkills)
                    job_profile_id, job_criteria_map = get_job_criteria(mongoid, account_name, account_config)
                    logger.critical("found job profile id %s", job_profile_id)
                    if job_profile_id:

                        
                        print("################################################")
                        print(job_criteria_map)
                        if len(findSkills) == 0 and job_profile_id and job_profile_id in job_criteria_map:
                            
                            criteria = job_criteria_map[job_profile_id]
                            findSkills = []
                            if "skills" in criteria:
                                for value in criteria['skills']["values"]:
                                    findSkills.append(value["value"])

                            logger.critical("find skills for job %s", findSkills)
                            ret = extractSkill(findSkills, mongoid, False, account_name, account_config)
                            ret = json.dumps(ret,default=str)
                        else:

                            ret = {}
                            for job_id in job_criteria_map:

                                criteria = job_criteria_map[job_id]
                                findSkills = []
                                if "skills" in criteria:
                                    for value in criteria['skills']["values"]:
                                        findSkills.append(value["value"])

                                retSkill = extractSkill(findSkills, mongoid, False, account_name, account_config)
                                avg_value = 0
                                if mongoid in retSkill:
                                    for key in retSkill[mongoid]["skill"]:
                                        avg_value += retSkill[mongoid]["skill"][key]

                                    if len(retSkill[mongoid]["skill"]) > 0:
                                        retSkill[mongoid]["avg"] = avg_value/len(retSkill[mongoid]["skill"])
                                    else:
                                        retSkill[mongoid]["avg"] = 0
                                        
                                    ret[job_id] = retSkill[mongoid]
                                else:
                                    ret[job_id] = {} 
                            
                            ret = json.dumps(ret,default=str)

                    else:
                        retSkill = extractSkill(findSkills, mongoid, False, account_name, account_config)
                        logger.critical("find skill found %s", retSkill)
                        avg_value = 0
                        if mongoid in retSkill:
                            for key in retSkill[mongoid]["skill"]:
                                avg_value += retSkill[mongoid]["skill"][key]

                            if len(retSkill[mongoid]["skill"]) > 0:
                                retSkill[mongoid]["avg"] = avg_value/len(retSkill[mongoid]["skill"])
                            else:
                                retSkill[mongoid]["avg"] = 0
                                
                            ret[job_id] = retSkill[mongoid]
                        else:
                            ret[job_id] = {} 

                        logger.critical("find skill found %s", ret)
                        ret = json.dumps(ret,default=str)

                    if "filename" in body:
                        updateStats({
                            "action" : "resume_pipeline_update",
                            "resume_unique_key" : body["filename"],
                            "meta" : {
                                # "ret" : ret,
                                "mongoid" : body["mongoid"]
                            },
                            "stage" : {
                                "pipeline" : "skill_extract",
                            },
                            "account_name" : account_name,
                            "account_config" : account_config
                        })

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
                
                logger.critical("completed")
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

import subprocess
def main():

    result = subprocess.run(['gsutil', '-m', 'cp', '-rn',
                             'gs://general_ai_works/word2vec/', '/workspace/word2vec'], stdout=subprocess.PIPE)

    print(result)

    
    loadModel()
    loadDomainModel()
    
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