from app.logging import logger
import os
import pika
import json
ROUTING_KEY = 'rpc.classify.queue'
EXCHANGE = ""

amqp_url = os.getenv('RABBIT_DB',"amqp://guest:guest@rabbitmq:5672/%2F?connection_attempts=3&heartbeat=3600")


def handle(channel, method, properties, body):
    message = body.decode()
    logger.info("received: %s", message)
    return json.loads(message)


def sendBlockingMessage(obj):

    connection = pika.BlockingConnection(pika.URLParameters(amqp_url))
    channel = connection.channel()

    with connection, channel:
        message = json.dumps(obj)
        next(channel.consume(queue="amq.rabbitmq.reply-to", auto_ack=True,
                            inactivity_timeout=0.1))
        channel.basic_publish(
            exchange=EXCHANGE, routing_key=ROUTING_KEY, body=message.encode(),
            properties=pika.BasicProperties(reply_to="amq.rabbitmq.reply-to",expiration='300'))
        logger.info("sent: %s", message)

        for (method, properties, body) in channel.consume(
                queue="amq.rabbitmq.reply-to", auto_ack=True):
            return handle(channel, method, properties, body)


    