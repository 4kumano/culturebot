from __future__ import annotations
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
logger.propagate = False

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(FORMATTER)
console_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)

file_handler = RotatingFileHandler(LOG_FILE,maxBytes=0x100000,backupCount=2,encoding='utf-8')
file_handler.setFormatter(FORMATTER)
logger.addHandler(file_handler)

if __name__ == '__main__':
    # make an example config
    empty_config = ConfigParser()
    empty_config.read('config.cfg')
    
    for section in empty_config:
        for key in empty_config[section]:
            empty_config[section][key] = ''
    empty_config.set('bot', 'prefix', config.get('bot', 'prefix'))
    empty_config.write(open('config_.cfg', 'w'), False)