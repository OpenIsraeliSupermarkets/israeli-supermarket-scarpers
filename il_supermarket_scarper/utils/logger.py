
from asyncio.log import logger


def set_logger():
    import logging
    from sys import stdout

    # Define logger
    logger = logging.getLogger('mylogger')

    if not logger.handlers:
        logger.setLevel(logging.DEBUG) # set logger level
        logFormatter = logging.Formatter\
        ("%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s")
        consoleHandler = logging.StreamHandler(stdout) #set streamhandler to stdout
        consoleHandler.setFormatter(logFormatter)
        logger.addHandler(consoleHandler)

    return logger
class Logger:
    logger = set_logger()

    @staticmethod
    def info(msg, *args, **kwargs):
        logger.info(msg, *args, **kwargs)

    @staticmethod
    def error(msg, *args, **kwargs):
        logger.error(msg, *args, **kwargs)