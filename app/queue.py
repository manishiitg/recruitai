from rq import Queue
from redis import Redis
from app.logging import logger
from app.config import REDIS_HOST
from app.config import REDIS_PORT


# Tell RQ what Redis connection to use
redis_conn = Redis(REDIS_HOST, REDIS_PORT)
q = Queue(connection=redis_conn)  # no args implies the default queue
