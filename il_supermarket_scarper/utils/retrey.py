import logging
import random
import time

from datetime import datetime
from functools import partial

import functools


try:
    from decorator import decorator
except ImportError:

    def decorator(caller):
        """Turns caller into a decorator.
        Unlike decorator module, function signature is not preserved.

        :param caller: caller(f, *args, **kwargs)
        """

        def decor(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return caller(func, *args, **kwargs)

            return wrapper

        return decor


logging_logger = logging.getLogger(__name__)


def __retry_internal(  # pylint: disable=broad-except,too-many-locals
    func,
    exceptions=Exception,
    tries=-1,
    delay=0,
    max_delay=None,
    backoff=1,
    timeout=None,
    max_timeout=None,
    backoff_timeout=1,
    jitter=0,
    logger=logging_logger,
):
    """
    Executes a function and retries it if it failed.

    :param f: the function to execute.
    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :param logger: logger.warning(fmt, error, delay) will be called on failed attempts.
                   default: retry.logging_logger. if None, logging is disabled.
    :returns: the result of the f function.
    """
    _tries, _delay = tries, delay
    _timeout = timeout
    while _tries:
        datetime_start = datetime.now()
        try:
            if timeout:
                return func(timeout=_timeout)
            return func()
        except exceptions as error:  # pylint: disable=broad-except
            measured_seconds = (datetime.now() - datetime_start).total_seconds()
            _tries -= 1
            if not _tries:
                raise

            if logger is not None:
                logger.warning(
                    "%s, configured timeout %s,measured time to timeout %s ,retrying in %s seconds",
                    error,
                    _timeout,
                    measured_seconds,
                    _delay,
                )
                logger.error_execption(error)

            time.sleep(_delay)
            _delay *= backoff

            if _timeout:
                _timeout += backoff_timeout

            if isinstance(jitter, tuple):
                _delay += random.uniform(*jitter)
            else:
                _delay += jitter

            if max_delay is not None:
                _delay = min(_delay, max_delay)

            if max_timeout is not None:
                _timeout = min(_timeout, max_timeout)


def retry(
    exceptions=Exception,
    tries=-1,
    delay=0,
    max_delay=None,
    backoff=1,
    timeout=None,
    max_timeout=None,
    backoff_timeout=1,
    jitter=0,
    logger=logging_logger,
):
    """Returns a retry decorator.

    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :param logger: logger.warning(fmt, error, delay) will be called on failed attempts.
                   default: retry.logging_logger. if None, logging is disabled.
    :returns: a retry decorator.
    """

    @decorator
    def retry_decorator(func, *fargs, **fkwargs):
        args = fargs if fargs else []
        kwargs = fkwargs if fkwargs else {}
        return __retry_internal(
            partial(func, *args, **kwargs),
            exceptions,
            tries,
            delay,
            max_delay,
            backoff,
            timeout,
            max_timeout,
            backoff_timeout,
            jitter,
            logger,
        )

    return retry_decorator


def retry_call(
    func,
    fargs=None,
    fkwargs=None,
    exceptions=Exception,
    tries=-1,
    delay=0,
    max_delay=None,
    backoff=1,
    jitter=0,
    logger=logging_logger,
):
    """
    Calls a function and re-executes it if it failed.

    :param f: the function to execute.
    :param fargs: the positional arguments of the function to execute.
    :param fkwargs: the named arguments of the function to execute.
    :param exceptions: an exception or a tuple of exceptions to catch. default: Exception.
    :param tries: the maximum number of attempts. default: -1 (infinite).
    :param delay: initial delay between attempts. default: 0.
    :param max_delay: the maximum value of delay. default: None (no limit).
    :param backoff: multiplier applied to delay between attempts. default: 1 (no backoff).
    :param jitter: extra seconds added to delay between attempts. default: 0.
                   fixed if a number, random if a range tuple (min, max)
    :param logger: logger.warning(fmt, error, delay) will be called on failed attempts.
                   default: retry.logging_logger. if None, logging is disabled.
    :returns: the result of the f function.
    """
    args = fargs if fargs else []
    kwargs = fkwargs if fkwargs else {}
    return __retry_internal(
        partial(func, *args, **kwargs),
        exceptions,
        tries,
        delay,
        max_delay,
        backoff,
        jitter,
        logger,
    )
