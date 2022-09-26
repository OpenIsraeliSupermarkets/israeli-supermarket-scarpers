import logging


def set_logger():
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

        fileHandler = logging.FileHandler("logging.log")
        fileHandler.setFormatter(logFormatter)
        logger.addHandler(fileHandler)


    return logger
class Logger:
    logger = set_logger()

    @classmethod
    def info(cls,msg, *args, **kwargs):
       cls.logger.info(msg, *args, **kwargs)

    @classmethod
    def error(cls,msg, *args, **kwargs):
        cls.logger.error(msg, *args, **kwargs)