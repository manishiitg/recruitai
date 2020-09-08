from app.logging import logger
import os
import pika
import json
ROUTING_KEY = 'rpc.filter.queue'
EXCHANGE = ""

amqp_url = os.getenv('RABBIT_DB')


def handle(channel, method, properties, body):
    if body is None:
        return body
    message = body.decode()
    logger.info("received: %s", message)
    return json.loads(message)


 # cb = functools.partial(self.acknowledge_message, delivery_tag)
# self._connection.add_callback_threadsafe(cb)
# threadsafe callback is only on blocking connection

def getConnection():
    connection = pika.BlockingConnection(pika.URLParameters(amqp_url))
    channel = connection.channel()
    return connection, channel

def sendBlockingMessage(obj):

    connection, channel = getConnection()

    with connection, channel:
        message = json.dumps(obj)
        next(channel.consume(queue="amq.rabbitmq.reply-to", auto_ack=True,
                            inactivity_timeout=0.1))
        
        channel.basic_publish(
            exchange=EXCHANGE, routing_key=ROUTING_KEY, body=message.encode(),
            properties=pika.BasicProperties(reply_to="amq.rabbitmq.reply-to",expiration='300'))
    
        logger.info("sent: %s", message)

        for (method, properties, body) in channel.consume(
                queue="amq.rabbitmq.reply-to", auto_ack=True,inactivity_timeout=60):
            return handle(channel, method, properties, body)



    