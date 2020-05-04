import logging
import sys

import os
hostname = os.environ['HOSTNAME']

class ContextFilter(logging.Filter):
    """
    This is a filter which injects contextual information into the log.
    """
    def filter(self, record):
        record.hostname = hostname
        return True


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(hostname)s - %(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)
logger.addFilter(ContextFilter())
