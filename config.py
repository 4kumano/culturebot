import logging
import sys
from configparser import ConfigParser
from logging.handlers import RotatingFileHandler

config = ConfigParser()
config.read('config.cfg')

FORMATTER = logging.Formatter("{asctime} :: {levelname:5s} :: {message}",style='{')
LOG_FILE = "logs/culturebot.log"

logging.basicConfig()
logger = logging.getLogger('culturebot')
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(FORMATTER)
console_handler.setLevel(logging.DEBUG)
file_handler = RotatingFileHandler(LOG_FILE,maxBytes=0x100000,backupCount=2,encoding='utf-8')
file_handler.setFormatter(FORMATTER)
logger.addHandler(console_handler)
logger.addHandler(file_handler)
logger.propagate = False

