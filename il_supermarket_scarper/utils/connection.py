
from urllib.error import URLError
from http.client import RemoteDisconnected
from retry import retry
import socket
import requests

from .logger import Logger


RETRIVE_EXECPTION = (URLError,RemoteDisconnected,ConnectionResetError,socket.gaierror,socket.timeout)


def download_connection_retry():
    def wrapper(func):

        @retry(exceptions=RETRIVE_EXECPTION,tries=5,delay=2,backoff=2,max_delay=30,logger=Logger)
        def inner(*args, **kwargs):
            socket.setdefaulttimeout(15)
            return func(*args, **kwargs)

        return inner

    return wrapper


def url_connection_retry():
    def wrapper(func):

        @retry(exceptions=ConnectionError, delay=5, tries=6,logger=Logger)
        def inner(*args, **kwargs):
            return func(*args, **kwargs)

        return inner

    return wrapper

def get_ip():
    response = requests.get('https://api64.ipify.org?format=json').json()
    return response["ip"]

def get_location():
    ip_address = get_ip()
    response = requests.get(f'https://ipapi.co/{ip_address}/json/').json()
    location_data = {
        "ip": ip_address,
        "city": response.get("city"),
        "region": response.get("region"),
        "country": response.get("country_name")
    }
    return location_data

def disable_when_outside_israel(function):
    
    def _decorator():
        Logger.warning(f"test {function.__name__ } has been disabled! can't scarper Gov.il site outside IL region.")
    
    estimated_location = get_location()

    if estimated_location['country'] != "Israel":
        Logger.info(f"estimated location is {str(estimated_location)}")
        return _decorator
    else:
        return function