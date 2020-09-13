from app.logging import logger
import os
import pika
import json
import time

ROUTING_KEY = 'rpc.filter.queue'
EXCHANGE = ""

from app.publisher.connection import getConnection

def handle(channel, method, properties, body):
    if body is None:
        return body
        
    message = body.decode()
    logger.info("received: %s", message)
    
    return json.loads(message)
    

 # cb = functools.partial(self.acknowledge_message, delivery_tag)
# self._connection.add_callback_threadsafe(cb)
# threadsafe callback is only on blocking connection

def sendBlockingMessage(obj):

    start_time = time.time()
    
    connection, channel = getConnection()

    print("--- %s get connection ---" % (time.time() - start_time))


    # with connection, channel:
    message = json.dumps(obj)
    next(channel.consume(queue="amq.rabbitmq.reply-to", auto_ack=True,
                        inactivity_timeout=0.1))

    print("--- %s channel consume ---" % (time.time() - start_time))

    channel.basic_publish(
        exchange=EXCHANGE, routing_key=ROUTING_KEY, body=message.encode(),
        properties=pika.BasicProperties(reply_to="amq.rabbitmq.reply-to",expiration='3000'))
    logger.info("sent: %s", message)
    print("--- %s message sent ---" % (time.time() - start_time))


    for (method, properties, body) in channel.consume(
            queue="amq.rabbitmq.reply-to", auto_ack=True,inactivity_timeout=60):
        return handle(channel, method, properties, body)



    