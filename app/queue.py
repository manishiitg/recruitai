from rq import Queue
from redis import Redis
from app.logging import logger

# Tell RQ what Redis connection to use
redis_conn = Redis()
q = Queue(connection=redis_conn)  # no args implies the default queue
