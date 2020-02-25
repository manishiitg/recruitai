 from app.logging import logger as LOGGER
import os
import pika
import functools
import time
import json

SERVER_QUEUE = 'rpc.classify.queue'

amqp_url = os.getenv('RABBIT_DB',"amqp://guest:guest@rabbitmq:5672/%2F?connection_attempts=3&heartbeat=3600")

def sendBlockingMessage():
     """ Here, Client sends "Marco" to RPC Server, and RPC Server replies with
    "Polo".
    NOTE Normally, the server would be running separately from the client, but
    in this very simple example both are running in the same thread and sharing
    connection and channel.
    """
    
    with pika.BlockingConnection(pika.URLParameters(amqp_url)) as conn:
        channel = conn.channel()

        # Set up client

        # NOTE Client must create its consumer and publish RPC requests on the
        # same channel to enable the RabbitMQ broker to make the necessary
        # associations.
        #
        # Also, client must create the consumer *before* starting to publish the
        # RPC requests.
        #
        # Client must create its consumer with no_ack=True, because the reply-to
        # queue isn't real.

        channel.basic_consume(on_client_rx_reply_from_server,
                              queue='amq.rabbitmq.reply-to',
                              no_ack=True)
        channel.basic_publish(
            exchange='',
            routing_key=SERVER_QUEUE,
            body='Marco',
            properties=pika.BasicProperties(reply_to='amq.rabbitmq.reply-to'))

        channel.start_consuming()

def on_client_rx_reply_from_server(ch, method_frame, properties, body):
    print('RPC Client got reply:', body)

    # NOTE A real client might want to make additional RPC requests, but in this
    # simple example we're closing the channel after getting our first reply
    # to force control to return from channel.start_consuming()
    print('RPC Client says bye')
    ch.close()