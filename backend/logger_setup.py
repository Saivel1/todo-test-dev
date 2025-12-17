import logging
from dotenv import load_dotenv
import os
import sys

load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
stdout_handler = logging.StreamHandler(sys.stdout)


formatter_1 = logging.Formatter(
    fmt='[%(asctime)s] #%(levelname)-8s %(filename)s:'
        '%(lineno)d - %(name)s:%(funcName)s - %(message)s'
)

stdout_handler.setFormatter(formatter_1)

logger.addHandler(stdout_handler)