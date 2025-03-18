# Written by Rune Johannesen, (c)2023
from logging import Logger, handlers, Formatter, getLogger, INFO
from os import mkdir, getcwd, chdir
from os.path import dirname, join, exists, realpath
import sys


CURRENT_DIR: str = getcwd()
if getattr(sys, 'frozen', False):
    CURRENT_DIR: str = dirname(sys.executable)
else: CURRENT_DIR: str = dirname(realpath(__file__))
chdir(CURRENT_DIR)

def setup_logger(name: str) -> Logger:
    log_dir: str = "LOG"
    logging_dir: str = join(CURRENT_DIR, log_dir)
    if not exists(logging_dir): mkdir(logging_dir)
    log_full_path: str = join(CURRENT_DIR, log_dir, name+".log")
    log_format = Formatter('%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    log_handler = handlers.TimedRotatingFileHandler(log_full_path, 'midnight', 1, backupCount=180)
    log_handler.setFormatter(log_format)
    logger = getLogger(name)
    logger.setLevel(INFO)
    logger.addHandler(log_handler)
    return(logger)