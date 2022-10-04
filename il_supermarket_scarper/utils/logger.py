import logging
from sys import stdout


def build_logger():
    """create the logger instance"""
    # Define logger
    logger = logging.getLogger("mylogger")

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)  # set logger level
        log_formatter = logging.Formatter(
            "%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s"
        )
        console_handler = logging.StreamHandler(stdout)  # set streamhandler to stdout
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)

        file_handler = logging.FileHandler("logging.log")
        file_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)

    return logger


class Logger:
    """a static logger class to share will all components"""

    logger = build_logger()

    @classmethod
    def info(cls, msg, *args, **kwargs):
        """log info"""
        cls.logger.info(msg, *args, **kwargs)

    @classmethod
    def error(cls, msg, *args, **kwargs):
        """log error"""
        cls.logger.error(msg, *args, **kwargs)

    @classmethod
    def warning(cls, msg, *args, **kwargs):
        """log warning"""
        cls.logger.warning(msg, *args, **kwargs)
