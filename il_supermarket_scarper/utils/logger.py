import logging
import sys


def build_logger():
    """create the logger instance"""
    # Define logger
    logger = logging.getLogger("Logger")

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)  # set logger level
        log_formatter = logging.Formatter(
            "%(name)-12s %(asctime)s %(levelname)-8s %(filename)s:%(funcName)s %(message)s"
        )
        console_handler = logging.StreamHandler(
            sys.stdout
        )  # set streamhandler to stdout
        console_handler.setFormatter(log_formatter)
        logger.addHandler(console_handler)

        file_handler = logging.FileHandler("logging.log")
        file_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)

    return logger


class Logger:
    """a static logger class to share will all components"""

    enabled = True
    logger = build_logger()

    @classmethod
    def change_logging_status(cls, new_status):
        """enable or disable status"""
        cls.enabled = new_status

    @classmethod
    def info(cls, msg, *args, **kwargs):
        """log info"""
        if cls.enabled:
            cls.logger.info(msg, *args, **kwargs)

    @classmethod
    def error(cls, msg, *args, **kwargs):
        """log error"""
        if cls.enabled:
            cls.logger.error(msg, *args, **kwargs)

    @classmethod
    def error_execption(cls, _):
        """log execption"""
        if cls.enabled:
            cls.logger.error(
                "got an execption:",
                exc_info=sys.exc_info(),
            )

    @classmethod
    def warning(cls, msg, *args, **kwargs):
        """log warning"""
        if cls.enabled:
            cls.logger.warning(msg, *args, **kwargs)
