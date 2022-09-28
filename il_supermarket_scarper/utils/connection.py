
from urllib.error import URLError
from http.client import RemoteDisconnected
from retry import retry
import socket

RETRIVE_EXECPTION = (URLError,RemoteDisconnected,ConnectionResetError,socket.gaierror,socket.timeout)


def download_connection_retry():
    def wrapper(func):

        @retry(exceptions=RETRIVE_EXECPTION,tries=5,delay=2,backoff=2,max_delay=30)
        def inner(*args, **kwargs):
            import socket
            socket.setdefaulttimeout(15)
            return func(*args, **kwargs)

        return inner

    return wrapper


def url_connection_retry():
    def wrapper(func):

        @retry(exceptions=ConnectionError, delay=5, tries=6)
        def inner(*args, **kwargs):
            return func(*args, **kwargs)

        return inner

    return wrapper
