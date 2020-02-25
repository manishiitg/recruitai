
import pika


SERVER_QUEUE = 'rpc.classify.queue'


def main():
    with pika.BlockingConnection(pika.URLParameters(amqp_url)) as conn:
        channel = conn.channel()

        # Set up server

        channel.queue_declare(queue=SERVER_QUEUE,
                              exclusive=True,
                              auto_delete=True)
        channel.basic_consume(on_server_rx_rpc_request, queue=SERVER_QUEUE)
    
        channel.start_consuming()


def on_server_rx_rpc_request(ch, method_frame, properties, body):
    print('RPC Server got request:', body)

    ch.basic_publish('', routing_key=properties.reply_to, body='Polo')

    ch.basic_ack(delivery_tag=method_frame.delivery_tag)

    print('RPC Server says good bye')
