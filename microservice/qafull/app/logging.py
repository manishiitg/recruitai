import logging
import sys

logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)

# handler = logging.StreamHandler(sys.stdout)
# handler.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)

# logger.addHandler(handler)
# # 