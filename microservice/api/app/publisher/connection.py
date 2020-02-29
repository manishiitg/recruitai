from app.logging import logger
import os
import pika
import json

amqp_url = os.environ.get('RABBIT_DB',"amqp://guest:guest@rabbitmq:5672/%2F?connection_attempts=3&heartbeat=3600")


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