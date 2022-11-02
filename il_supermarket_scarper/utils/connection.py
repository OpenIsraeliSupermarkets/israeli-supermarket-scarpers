from urllib.error import URLError
from http.client import RemoteDisconnected
from http.cookiejar import MozillaCookieJar

import os
import socket
import requests

from retry import retry
from urllib3.exceptions import ReadTimeoutError
from requests.exceptions import ReadTimeout
from .logger import Logger


exceptions = (
    URLError,
    RemoteDisconnected,
    ConnectionResetError,
    socket.gaierror,
    socket.timeout,
    ConnectionError,
    ReadTimeout,
    ReadTimeoutError,
)


def download_connection_retry():
    """decorator the define the retry logic of connections tring to download files"""

    def wrapper(func):
        @retry(
            exceptions=exceptions,
            tries=6,
            delay=2,
            backoff=2,
            max_delay=64,
            logger=Logger,
        )
        def inner(*args, **kwargs):
            socket.setdefaulttimeout(15)
            return func(*args, **kwargs)

        return inner

    return wrapper


def url_connection_retry():
    """decorator the define the retry logic of connections tring to send get request"""

    def wrapper(func):
        @retry(
            exceptions=exceptions,
            tries=6,
            delay=2,
            backoff=2,
            max_delay=64,
            logger=Logger,
        )
        def inner(*args, **kwargs):
            socket.setdefaulttimeout(15)
            return func(*args, **kwargs)

        return inner

    return wrapper


def get_ip():
    """get the ip of the computer running the code"""
    response = requests.get("https://api64.ipify.org?format=json", timeout=10).json()
    return response["ip"]


def get_location():
    """get the estimated location of the computer running the code"""
    ip_address = get_ip()
    response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=10).json()
    location_data = {
        "ip": ip_address,
        "city": response.get("city"),
        "region": response.get("region"),
        "country": response.get("country_name"),
    }
    return location_data


def disable_when_outside_israel(function):
    """decorator to disable tests that scrap gov.il site to run outside israel region"""

    def _decorator():
        Logger.warning(
            f"test {function.__name__ } has been disabled!"
            "can't scarper Gov.il site outside IL region."
        )

    estimated_location = get_location()

    if estimated_location["country"] != "Israel":
        Logger.info(f"estimated location is {str(estimated_location)}")
        return _decorator
    return function


@url_connection_retry()
def session_and_check_status(url):
    """use a session to load the response and check status"""
    Logger.info(f"On a new Session: calling {url}")
    session = requests.Session()

    # get the download link
    response_content = session.get(url)
    if response_content.status_code != 200:
        Logger.info(
            f"Got status code: {response_content.status_code}"
            f"body is {response_content.text}"
        )
        raise ConnectionError(
            f"response for {url}, returned with "
            "status {response_content.status_code}"
        )
    return response_content


@url_connection_retry()
def session_with_cookies(chain, url):
    """request resource with cookies enabled"""

    session = requests.Session()
    session.cookies = MozillaCookieJar(f"{chain}_cookies.txt")
    try:
        session.cookies.load()
    except FileNotFoundError:
        Logger.info("didn't find cookie file")

    Logger.info(f"On a new Session requesting url: {url}")

    response_content = session.get(url)

    if response_content.status_code != 200:
        Logger.info(
            f"On Session, Got status code: {response_content.status_code}"
            f", body is {response_content.text} "
        )
        raise ConnectionError(
            f"response for {url}, returned with status"
            f" {response_content.status_code}"
        )

    if not os.path.exists(f"{chain}_cookies.txt"):
        session.cookies.save()
    return response_content


@url_connection_retry()
def request_and_check_status(url):

    """request resource and check the output"""
    Logger.info(f"Requesting url: {url}")
    req_res = requests.get(url)

    if req_res.status_code != 200:
        Logger.info(f"Got status code: {req_res.status_code}, body is {req_res.text}")
        raise ConnectionError(
            f"response for {url}, returned with status {req_res.status_code}"
        )

    return req_res
