import functools
import time
from app.logging import logger as LOGGER
import pika
from app.resumeutil import fullResumeParsing
import json
import threading
import redis
import os 

from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId


from app.account import initDB, connect_redis, r_exists, r_get, r_set

import traceback

import requests

amqp_url = os.getenv('RABBIT_DB')

from app.publishskill import sendBlockingMessage as extractSkillMessage
from app.publishfilter import sendBlockingMessage as extractCandidateScore
from app.pushlishskillindex import sendMessage as indexcandidateskill

from app.publishcandidate import sendMessage as extractCandidateClassifySkill
from app.publishsummary import sendMessage as sendSummary
from app.publishdatasync import sendMessage as datasync
from app.statspublisher import sendMessage as updateStats
from app.publishqa import sendMessage as updateQA
from app.publisherqafull import sendMessage as publisherqafull


class TaskQueue(object):
    """This is an example consumer that will handle unexpected interactions
    with RabbitMQ such as channel and connection closures.
    If RabbitMQ closes the connection, this class will stop and indicate
    that reconnection is necessary. You should look at the output, as
    there are limited reasons why the connection may be closed, which
    usually are tied to permission related issues or socket timeouts.
    If the channel is closed, it will indicate a problem with one of the
    commands that were issued and that should surface in the output as well.
    """
    EXCHANGE = 'message'
    EXCHANGE_TYPE = 'topic'
    QUEUE = 'resume'
    ROUTING_KEY = 'resume.parsing'
    def __init__(self, amqp_url):
        """Create a new instance of the consumer class, passing in the AMQP
        URL used to connect to RabbitMQ.
        :param str amqp_url: The AMQP url to connect with
        """
        self.should_reconnect = False
        self.was_consuming = False

        self._connection = None
        self._channel = None
        self._closing = False
        self._consumer_tag = None
        self._url = amqp_url
        self._consuming = False
        self.threads = [    ]
        # In production, experiment with higher prefetch values
        # for higher consumer throughput
        self._prefetch_count = int(os.getenv("RESUME_PARALLEL_PROCESS", 1))


    def connect(self):
        """This method connects to RabbitMQ, returning the connection handle.
        When the connection is established, the on_connection_open method
        will be invoked by pika.
        :rtype: pika.SelectConnection
        """
        # LOGGER.info('Connecting to %s', self._url)
        return pika.SelectConnection(
            parameters=pika.URLParameters(self._url),
            on_open_callback=self.on_connection_open,
            on_open_error_callback=self.on_connection_open_error,
            on_close_callback=self.on_connection_closed)

    def close_connection(self):
        self._consuming = False
        if self._connection.is_closing or self._connection.is_closed:
            # LOGGER.info('Connection is closing or already closed')
            pass
        else:
            # LOGGER.info('Closing connection')
            self._connection.close()

    def on_connection_open(self, _unused_connection):
        """This method is called by pika once the connection to RabbitMQ has
        been established. It passes the handle to the connection object in
        case we need it, but in this case, we'll just mark it unused.
        :param pika.SelectConnection _unused_connection: The connection
        """
        # LOGGER.info('Connection opened')
        self.open_channel()

    def on_connection_open_error(self, _unused_connection, err):
        """This method is called by pika if the connection to RabbitMQ
        can't be established.
        :param pika.SelectConnection _unused_connection: The connection
        :param Exception err: The error
        """
        # LOGGER.error('Connection open failed: %s', err)
        self.reconnect()

    def on_connection_closed(self, _unused_connection, reason):
        """This method is invoked by pika when the connection to RabbitMQ is
        closed unexpectedly. Since it is unexpected, we will reconnect to
        RabbitMQ if it disconnects.
        :param pika.connection.Connection connection: The closed connection obj
        :param Exception reason: exception representing reason for loss of
            connection.
        """
        self._channel = None
        if self._closing:
            self._connection.ioloop.stop()
        else:
            # LOGGER.warning('Connection closed, reconnect necessary: %s', reason)
            self.reconnect()

    def reconnect(self):
        """Will be invoked if the connection can't be opened or is
        closed. Indicates that a reconnect is necessary then stops the
        ioloop.
        """
        self.should_reconnect = True
        self.stop()

    def open_channel(self):
        """Open a new channel with RabbitMQ by issuing the Channel.Open RPC
        command. When RabbitMQ responds that the channel is open, the
        on_channel_open callback will be invoked by pika.
        """
        # LOGGER.info('Creating a new channel')
        self._connection.channel(on_open_callback=self.on_channel_open)

    def on_channel_open(self, channel):
        """This method is invoked by pika when the channel has been opened.
        The channel object is passed in so we can make use of it.
        Since the channel is now open, we'll declare the exchange to use.
        :param pika.channel.Channel channel: The channel object
        """
        # LOGGER.info('Channel opened')
        self._channel = channel
        self.add_on_channel_close_callback()
        self.setup_exchange(self.EXCHANGE)

    def add_on_channel_close_callback(self):
        """This method tells pika to call the on_channel_closed method if
        RabbitMQ unexpectedly closes the channel.
        """
        # LOGGER.info('Adding channel close callback')
        self._channel.add_on_close_callback(self.on_channel_closed)

    def on_channel_closed(self, channel, reason):
        """Invoked by pika when RabbitMQ unexpectedly closes the channel.
        Channels are usually closed if you attempt to do something that
        violates the protocol, such as re-declare an exchange or queue with
        different parameters. In this case, we'll close the connection
        to shutdown the object.
        :param pika.channel.Channel: The closed channel
        :param Exception reason: why the channel was closed
        """
        # LOGGER.warning('Channel %i was closed: %s', channel, reason)
        self.close_connection()

    def setup_exchange(self, exchange_name):
        """Setup the exchange on RabbitMQ by invoking the Exchange.Declare RPC
        command. When it is complete, the on_exchange_declareok method will
        be invoked by pika.
        :param str|unicode exchange_name: The name of the exchange to declare
        """
        # LOGGER.info('Declaring exchange: %s', exchange_name)
        # Note: using functools.partial is not required, it is demonstrating
        # how arbitrary data can be passed to the callback when it is called
        cb = functools.partial(
            self.on_exchange_declareok, userdata=exchange_name)
        self._channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=self.EXCHANGE_TYPE,
            callback=cb)

    def on_exchange_declareok(self, _unused_frame, userdata):
        """Invoked by pika when RabbitMQ has finished the Exchange.Declare RPC
        command.
        :param pika.Frame.Method unused_frame: Exchange.DeclareOk response frame
        :param str|unicode userdata: Extra user data (exchange name)
        """
        # LOGGER.info('Exchange declared: %s', userdata)
        self.setup_queue(self.QUEUE)

    def setup_queue(self, queue_name):
        """Setup the queue on RabbitMQ by invoking the Queue.Declare RPC
        command. When it is complete, the on_queue_declareok method will
        be invoked by pika.
        :param str|unicode queue_name: The name of the queue to declare.
        """
        # LOGGER.info('Declaring queue %s', queue_name)
        cb = functools.partial(self.on_queue_declareok, userdata=queue_name)
        self._channel.queue_declare(queue=queue_name, durable=True, callback=cb, arguments = {'x-max-priority': 10})

    def on_queue_declareok(self, _unused_frame, userdata):
        """Method invoked by pika when the Queue.Declare RPC call made in
        setup_queue has completed. In this method we will bind the queue
        and exchange together with the routing key by issuing the Queue.Bind
        RPC command. When this command is complete, the on_bindok method will
        be invoked by pika.
        :param pika.frame.Method _unused_frame: The Queue.DeclareOk frame
        :param str|unicode userdata: Extra user data (queue name)
        """
        queue_name = userdata
        # LOGGER.info('Binding %s to %s with %s', self.EXCHANGE, queue_name,
        #             self.ROUTING_KEY)
        cb = functools.partial(self.on_bindok, userdata=queue_name)
        self._channel.queue_bind(
            queue_name,
            self.EXCHANGE,
            routing_key=self.ROUTING_KEY,
            callback=cb)

    def on_bindok(self, _unused_frame, userdata):
        """Invoked by pika when the Queue.Bind method has completed. At this
        point we will set the prefetch count for the channel.
        :param pika.frame.Method _unused_frame: The Queue.BindOk response frame
        :param str|unicode userdata: Extra user data (queue name)
        """
        # LOGGER.info('Queue bound: %s', userdata)
        self.set_qos()

    def set_qos(self):
        """This method sets up the consumer prefetch to only be delivered
        one message at a time. The consumer must acknowledge this message
        before RabbitMQ will deliver another one. You should experiment
        with different prefetch values to achieve desired performance.
        """
        self._channel.basic_qos(
            prefetch_count=self._prefetch_count, callback=self.on_basic_qos_ok)

    def on_basic_qos_ok(self, _unused_frame):
        """Invoked by pika when the Basic.QoS method has completed. At this
        point we will start consuming messages by calling start_consuming
        which will invoke the needed RPC commands to start the process.
        :param pika.frame.Method _unused_frame: The Basic.QosOk response frame
        """
        # LOGGER.info('QOS set to: %d', self._prefetch_count)
        self.start_consuming()

    def start_consuming(self):
        """This method sets up the consumer by first calling
        add_on_cancel_callback so that the object is notified if RabbitMQ
        cancels the consumer. It then issues the Basic.Consume RPC command
        which returns the consumer tag that is used to uniquely identify the
        consumer with RabbitMQ. We keep the value to use it when we want to
        cancel consuming. The on_message method is passed in as a callback pika
        will invoke when a message is fully received.
        """
        # LOGGER.info('Issuing consumer related RPC commands')
        self.add_on_cancel_callback()
        self._consumer_tag = self._channel.basic_consume(
            self.QUEUE, self.on_message)
        self.was_consuming = True
        self._consuming = True

    def add_on_cancel_callback(self):
        """Add a callback that will be invoked if RabbitMQ cancels the consumer
        for some reason. If RabbitMQ does cancel the consumer,
        on_consumer_cancelled will be invoked by pika.
        """
        # LOGGER.info('Adding consumer cancellation callback')
        self._channel.add_on_cancel_callback(self.on_consumer_cancelled)

    def on_consumer_cancelled(self, method_frame):
        """Invoked by pika when RabbitMQ sends a Basic.Cancel for a consumer
        receiving messages.
        :param pika.frame.Method method_frame: The Basic.Cancel frame
        """
        # LOGGER.info('Consumer was cancelled remotely, shutting down: %r',
                    # method_frame)
        if self._channel:
            self._channel.close()

    def on_message(self, _unused_channel, basic_deliver, properties, body):
        """Invoked by pika when a message is delivered from RabbitMQ. The
        channel is passed for your convenience. The basic_deliver object that
        is passed in carries the exchange, routing key, delivery tag and
        a redelivered flag for the message. The properties passed in is an
        instance of BasicProperties with the message properties and the body
        is the message that was sent.
        :param pika.channel.Channel _unused_channel: The channel object
        :param pika.Spec.Basic.Deliver: basic_deliver method
        :param pika.Spec.BasicProperties: properties
        :param bytes body: The message body
        """
        # LOGGER.info('Received message # %s from %s: %s',
        #             basic_deliver.delivery_tag, properties.app_id, body)

        delivery_tag = basic_deliver.delivery_tag
        t = threading.Thread(target=self.do_work, kwargs=dict(delivery_tag=delivery_tag, body=body))
        t.start()
        LOGGER.info(t.is_alive())
        self.threads.append(t)

        # self.acknowledge_message(basic_deliver.delivery_tag)

    def do_work(self, delivery_tag, body):
        thread_id = threading.get_ident()
        fmt1 = 'Thread id: {} Delivery tag: {} Message body: {}'
        # print(fmt1.format(thread_id, delivery_tag, body))
        # LOGGER.info(fmt1.format(thread_id, delivery_tag, body))
        
        message = json.loads(body)
        LOGGER.critical(body)

        account_name = None
        if "account_name" in message:
            account_name = message["account_name"]
        else:
            LOGGER.critical("no account found. unable to proceed")
            return self.acknowledge_message(delivery_tag)

        
        account_config = message["account_config"]

        if "mongoid" not in message:
            message["mongoid"] = ""
            
        if message["mongoid"] is None:
            message["mongoid"] = ""

        if "skills" in message:
            skills = message["skills"]
        else:
            skills = None

        priority = 0

        if "priority" in message:
            LOGGER.critical("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%priority %s", message["priority"])
            priority = int(message["priority"])
        else:
            LOGGER.critical("priority not found")

        if not ObjectId.is_valid(message["mongoid"]):
            LOGGER.critical("invalid mongoid. unable to proceed")
            return self.acknowledge_message(delivery_tag)

        meta = {}
        if "meta" in message:
            meta = message["meta"]

        key = message["filename"]

        key = ''.join(e for e in key if e.isalnum()) 

        LOGGER.critical("redis key %s", key)

        doProcess = False

        r = connect_redis(account_name, account_config)

        updateStats({
            "action" : "resume_pipeline_update",
            "resume_unique_key" : message["filename"],
            "meta" : {
                "mongoid" : message["mongoid"]
            },
            "stage" : {
                "pipeline" : "resume_start",
                "priority" : message["priority"] 
            },
            "account_name" : account_name,
            "account_config" : account_config
        })

        if "finalImages" in message:
            if len(message["finalImages"]) >= 10:
                ret = {
                    "error" : "too many pages wont process it " + str(len(message["finalImages"]))
                }
                LOGGER.critical(ret)
                self.updateInDB(ret , message["mongoid"], message, account_name, account_config)
                self.acknowledge_message(delivery_tag)

                updateStats({
                    "action" : "resume_pipeline_update",
                    "resume_unique_key" : message["filename"],
                    "meta" : {
                        "error" : ret["error"],
                        "mongoid" : message["mongoid"]
                    },
                    "stage" : {
                        "pipeline" : "resume",
                        "priority" : message["priority"] 
                    },
                    "account_name" : account_name,
                    "account_config" : account_config
                })

                return
        
        db = initDB(account_name, account_config)
        candidate_row = db.emailStored.find_one({
            "_id" : ObjectId(message["mongoid"])
        })

        

        if not candidate_row:
            LOGGER.critical("candidate not found in db %s", message["mongoid"])
            return self.acknowledge_message(delivery_tag)

        has_job_profile = False
        # this needs to be changed after i think about candidate db
        job_profile_id = None
        if "job_profile_id" in candidate_row:
            job_profile_id = candidate_row["job_profile_id"]
            if len(job_profile_id) > 0:
                has_job_profile = True

        start_time = time.time()

        is_cache = False
        if r_exists(key, account_name, account_config) and False: # turning of cache because testing with ai models
            ret = r_get(key, account_name, account_config)
            ret = json.loads(ret)
            LOGGER.critical("redis key exists")
            if "error" not in ret:

                is_cache = True

                if "error" not in ret and ObjectId.is_valid(message["mongoid"]):
                    pass

                self.updateInDB(ret , message["mongoid"], message, account_name, account_config)
                if skills is None:
                    skills = ""

                if not isinstance(skills, list):
                    skills = skills.split(",")
                
                qa_parsing_type = "fast"
                if not has_job_profile:
                    qa_parsing_type = "mini"

                publisherqafull({
                    "action" : "qa_pipeline",
                    "mongoid" : message["mongoid"],
                    "filename" : message["filename"],
                    "parsing" : qa_parsing_type,
                    "account_name" : account_name,
                    "account_config" : account_config,
                    "priority" : message["priority"]
                })
                indexcandidateskill({
                    "action" : "extractSkill",
                    "mongoid" : message["mongoid"],
                    "filename" : message["filename"],
                    "skills" : skills,
                    # "meta" : meta,
                    "account_name" : account_name,
                    "account_config" : account_config
                })

                updateStats({
                    "action" : "resume_pipeline_update",
                    "resume_unique_key" : message["filename"],
                    "meta" : {
                        "mongoid" : message["mongoid"],
                        "is_cache" : is_cache
                    },
                    "stage" : {
                        "pipeline" : "resume",
                        "priority" : message["priority"] 
                    },
                    "account_name" : account_name,
                    "account_config" : account_config
                })
                
                extractCandidateClassifySkill({
                    "mongoid" : message["mongoid"],
                    "filename" : message["filename"],
                    "account_name" : account_name,
                    "account_config" : account_config,
                    "priority" : message["priority"] 
                })
                # if "criteria" in meta:
                #     extractCandidateScore({
                #         "action" : "candidate_score",
                #         "id" : message["mongoid"],
                #         "mongoid" : message["mongoid"],
                #         "filename" : message["filename"],
                #         "account_name" : account_name,
                #         "account_config" : account_config,
                #         "priority" : message["priority"],
                #         "criteria" : meta["criteria"]
                #     })

                sendSummary({
                    "mongoid": message["mongoid"],
                    "filename": message["filename"],
                    "priority": message["priority"],
                    "account_name": account_name,
                    "account_config": account_config
                })
                LOGGER.critical(" data sync calledddd 121221")
                datasync({
                    "id" : message["mongoid"],
                    "action" : "syncCandidate",
                    "account_name" : account_name,
                    "account_config" : account_config,
                    "priority" : message["priority"],
                    "field" : "tag_id"
                })

                self.notifyNodeSystem(ret, message["mongoid"], message, account_name, account_config)

            else:
                LOGGER.critical("redis key exists but previously error status so reprocessing")
                doProcess = True
        else:
            doProcess = True
                
        if doProcess:
            ret = fullResumeParsing(message["filename"], message["mongoid"], message , priority, account_name, account_config, candidate_row)
            if "parsing_type" in ret and ret["parsing_type"] is not "fast":
                r_set(key, json.dumps(ret), account_name, account_config) # 1day or 30days in dev
                
            if "error" not in ret and ObjectId.is_valid(message["mongoid"]):
                pass


            self.updateInDB(ret, message["mongoid"], message, account_name, account_config)
            if skills is None:
                skills = ""
            if not isinstance(skills, list):
                skills = skills.split(",")

            qa_parsing_type = "fast"
            
            if not has_job_profile:
                qa_parsing_type = "mini"

            if ret["parsing_type"] == "full":
                qa_parsing_type = "full"

            publisherqafull({  
                "action" : "qa_pipeline",
                "mongoid" : message["mongoid"],
                "filename" : message["filename"],
                "parsing" : qa_parsing_type,
                "account_name" : account_name,
                "account_config" : account_config,
                "priority" : message["priority"]
                })
            indexcandidateskill({
                "action" : "extractSkill",
                "mongoid" : message["mongoid"],
                "filename" : message["filename"],
                "skills" : skills,
                # "meta" : meta,
                "account_name" : account_name,
                "account_config" : account_config
            })
            updateStats({
                "action" : "resume_pipeline_update",
                "resume_unique_key" : message["filename"],
                "meta" : {
                    "mongoid" : message["mongoid"],
                    "is_cache" : is_cache
                },
                "stage" : {
                    "pipeline" : "resume",
                    "priority" : message["priority"] 
                },
                "account_name" : account_name,
                "account_config" : account_config
            })
            extractCandidateClassifySkill({
                "mongoid" : message["mongoid"],
                "filename" : message["filename"],
                "account_name" : account_name,
                "account_config" : account_config,
                "priority" : message["priority"] 
            })
            
            sendSummary({
                "mongoid": message["mongoid"],
                "filename": message["filename"],
                "priority": message["priority"],
                "account_name": account_name,
                "account_config": account_config
            })

            LOGGER.critical(" data sync calledddd")


            datasync({
                    "id" : message["mongoid"],
                    "action" : "syncCandidate",
                    "account_name" : account_name,
                    "account_config" : account_config,
                    "priority" : message["priority"],
                    "field" : "tag_id"
            })

            self.notifyNodeSystem(ret, message["mongoid"], message, account_name, account_config)

        LOGGER.critical("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ total time taken %s", (time.time() - start_time))    

        # cb = functools.partial(self.acknowledge_message, delivery_tag)
        # self._connection.add_callback_threadsafe(cb)
        # threadsafe callback is only on blocking connection

        self.acknowledge_message(delivery_tag)

    def updateInDB(self, ret, mongoid , message, account_name, account_config):
        isError = False
        if "error" in ret:
            isError = True
        ret = json.loads(json.dumps(ret))
        ret["ai_version_processed"] = "detectron4_flairtaggerv3.0_qa_model"
        ret["ai_version"] = "0.3"
        LOGGER.critical("mongo id %s", mongoid)
        if ObjectId.is_valid(mongoid):
            db = initDB(account_name, account_config)
            ret = db.emailStored.update_one({
                "_id" : ObjectId(mongoid)
            }, {
                "$set": {
                    "cvParsedInfo": ret,
                    "cvParsedAI": not isError,
                    "updatedTime" : datetime.now()
                }
            })
            LOGGER.critical(ret)

        else:
            LOGGER.critical("invalid mongoid")

    def notifyNodeSystem(self, ret, mongoid , message, account_name, account_config):
        isError = False
        if "error" in ret:
            isError = True
        try:
            if "meta" in message:
                LOGGER.critical("sending resume data to nodejs")
                meta = message["meta"]

                if "criteria" in meta:
                    del meta["criteria"]

                if "callback_url" in meta:
                    LOGGER.info("sending resume data to nodejs to url %s" , meta["callback_url"])
                    
                    message["parsed"] = {
                        # "cvParsedInfo": ret,
                        "cvParsedAI": not isError,
                        "updatedTime" : datetime.now()
                    }
                    meta["message"] = json.loads(json.dumps(message, default=str))
                    LOGGER.critical(meta)
                    x = requests.post(meta["callback_url"], json=meta)
                    LOGGER.critical(x.text)

        except Exception as e:
            LOGGER.critical(meta)
            traceback.print_exc()
            LOGGER.critical(e)

            
        

    def acknowledge_message(self, delivery_tag):
        """Acknowledge the message delivery from RabbitMQ by sending a
        Basic.Ack RPC method for the delivery tag.
        :param int delivery_tag: The delivery tag from the Basic.Deliver frame
        """
        # LOGGER.info('Acknowledging message %s', delivery_tag)

        if self._channel:
            self._channel.basic_ack(delivery_tag)

            

    def stop_consuming(self):
        """Tell RabbitMQ that you would like to stop consuming by sending the
        Basic.Cancel RPC command.
        """
        if self._channel:
            # LOGGER.info('Sending a Basic.Cancel RPC command to RabbitMQ')
            cb = functools.partial(
                self.on_cancelok, userdata=self._consumer_tag)
            self._channel.basic_cancel(self._consumer_tag, cb)

    def on_cancelok(self, _unused_frame, userdata):
        """This method is invoked by pika when RabbitMQ acknowledges the
        cancellation of a consumer. At this point we will close the channel.
        This will invoke the on_channel_closed method once the channel has been
        closed, which will in-turn close the connection.
        :param pika.frame.Method _unused_frame: The Basic.CancelOk frame
        :param str|unicode userdata: Extra user data (consumer tag)
        """
        self._consuming = False
        # LOGGER.info(
        #     'RabbitMQ acknowledged the cancellation of the consumer: %s',
        #     userdata)
        self.close_channel()

    def close_channel(self):
        """Call to close the channel with RabbitMQ cleanly by issuing the
        Channel.Close RPC command.
        """
        # LOGGER.info('Closing the channel')
        self._channel.close()

    def run(self):
        """Run the example consumer by connecting to RabbitMQ and then
        starting the IOLoop to block and allow the SelectConnection to operate.
        """
        self._connection = self.connect()
        self._connection.ioloop.start()

    def stop(self):
        """Cleanly shutdown the connection to RabbitMQ by stopping the consumer
        with RabbitMQ. When RabbitMQ confirms the cancellation, on_cancelok
        will be invoked by pika, which will then closing the channel and
        connection. The IOLoop is started again because this method is invoked
        when CTRL-C is pressed raising a KeyboardInterrupt exception. This
        exception stops the IOLoop which needs to be running for pika to
        communicate with RabbitMQ. All of the commands issued prior to starting
        the IOLoop will be buffered but not processed.
        """
        for thread in self.threads:
            thread.join()

        if not self._closing:
            self._closing = True
            # LOGGER.info('Stopping')
            if self._consuming:
                self.stop_consuming()
                self._connection.ioloop.start()
            else:
                self._connection.ioloop.stop()
            # LOGGER.info('Stopped')


class ReconnectingTaskQueue(object):
    """This is an example consumer that will reconnect if the nested
    ExampleConsumer indicates that a reconnect is necessary.
    """

    def __init__(self, amqp_url):
        self._reconnect_delay = 0
        self._amqp_url = amqp_url
        self._consumer = TaskQueue(self._amqp_url)

    def run(self):
        while True:
            try:
                self._consumer.run()
                # Wait for all to complete
            except KeyboardInterrupt:
                self._consumer.stop() 
                break
            # except Exception as e:
            #     print(traceback.format_exc())
            #     LOGGER.critical(str(e))
                
            self._maybe_reconnect()

    def _maybe_reconnect(self):
        if self._consumer.should_reconnect:
            self._consumer.stop()
            reconnect_delay = self._get_reconnect_delay()
            # LOGGER.info('Reconnecting after %d seconds', reconnect_delay)
            time.sleep(reconnect_delay)
            self._consumer = TaskQueue(self._amqp_url)

    def _get_reconnect_delay(self):
        if self._consumer.was_consuming:
            self._reconnect_delay = 0
        else:
            self._reconnect_delay += 1
        if self._reconnect_delay > 30:
            self._reconnect_delay = 30
        return self._reconnect_delay

from app.detectron.start import loadTrainedModel 
from app.cvlinepredict.start import loadModel
from app.ner.start import loadModel as loadModelTagger

import subprocess
import torch

def main():

    is_gpu_mandatory = int(os.getenv("GPU_MANDATORY", 0))
    if is_gpu_mandatory == 1:
        if not torch.cuda.is_available():
            LOGGER.critical("gpu is not there cannot start without it as it is mandatory")
            return


    result = subprocess.run(['gsutil', '-m', 'cp', '-rn',
                             'gs://general_ai_works/recruit-tags-flair-roberta-word2vec', '/workspace/recruit-tags-flair-roberta-word2vec'], stdout=subprocess.PIPE)

    print(result)

    result = subprocess.run(['gsutil', '-m', 'cp', '-rn',
                             'gs://recruitaiwork/detectron4_5000_fpn', '/workspace/detectron4_5000_fpn'], stdout=subprocess.PIPE)

    print(result)

    loadTrainedModel()
    # loadModel()
    loadModelTagger()
    consumer = ReconnectingTaskQueue(amqp_url)
    consumer.run()

if __name__ == '__main__':
    main()