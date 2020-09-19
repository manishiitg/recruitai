from app.logging import logger
import os
import pika
import json
ROUTING_KEY = 'rpc.filter.queue'
EXCHANGE = ""

amqp_url = os.environ.get('RABBIT_DB')


def handle(channel, method, properties, body):
    if body is None:
        return body
    message = body.decode()
    logger.critical("received: %s", message)
    return json.loads(message)


 # cb = functools.partial(self.acknowledge_message, delivery_tag)
# self._connection.add_callback_threadsafe(cb)
# threadsafe callback is only on blocking connection

connection = None 
channel = None
def getConnection():
    global connection 
    global channel

    if connection is None or not connection.is_open:
        logger.info("connection is not open======================================================")
        connection = pika.BlockingConnection(pika.URLParameters(amqp_url))
        channel = connection.channel()
    else:
        logger.info("connection reused===============================================")

    return connection, channel

def sendBlockingMessage(obj):

    try:
        
    
        connection, channel = getConnection()

        
        message = json.dumps(obj)
        next(channel.consume(queue="amq.rabbitmq.reply-to", auto_ack=True,
                            inactivity_timeout=10))
        channel.basic_publish(
            exchange=EXCHANGE, routing_key=ROUTING_KEY, body=message.encode(),
            properties=pika.BasicProperties(reply_to="amq.rabbitmq.reply-to",expiration='300'))
        logger.critical("send to filter")
        logger.info("sent to filter: %s", message)

        for (method, properties, body) in channel.consume(
                queue="amq.rabbitmq.reply-to", auto_ack=True,inactivity_timeout=300):
            return handle(channel, method, properties, body)

    except Exception as e:
        print(e)
        pass



    