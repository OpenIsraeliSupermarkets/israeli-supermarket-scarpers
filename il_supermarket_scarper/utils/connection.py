from urllib.error import URLError
from http.client import RemoteDisconnected
from http.cookiejar import MozillaCookieJar

import contextlib
import os
import socket
import random
import urllib
import requests


from urllib3.exceptions import ReadTimeoutError
from requests.exceptions import (
    ReadTimeout,
    ConnectionError as RequestsConnectionError,
    ChunkedEncodingError,
)
from cachetools import cached, TTLCache
from .logger import Logger
from .retrey import retry

exceptions = (
    URLError,
    RemoteDisconnected,
    ConnectionResetError,
    socket.gaierror,
    socket.timeout,
    ConnectionError,
    ReadTimeout,
    ReadTimeoutError,
    RequestsConnectionError,
    ChunkedEncodingError,
)


def download_connection_retry():
    """decorator the define the retry logic of connections tring to download files"""

    def wrapper(func):
        @retry(
            exceptions=exceptions,
            tries=8,
            delay=2,
            backoff=2,
            max_delay=5 * 60,
            logger=Logger,
            timeout=15,
            backoff_timeout=5,
        )
        def inner(*args, **kwargs):
            socket.setdefaulttimeout(kwargs.get("timeout", 15))
            del kwargs["timeout"]  # function don't get timeout param
            return func(*args, **kwargs)

        return inner

    return wrapper


def url_connection_retry():
    """decorator the define the retry logic of connections tring to send get request"""

    def wrapper(func):
        @retry(
            exceptions=exceptions,
            tries=8,
            delay=2,
            backoff=2,
            max_delay=5 * 60,
            logger=Logger,
            timeout=10,
            backoff_timeout=5,
        )
        def inner(*args, **kwargs):
            socket.setdefaulttimeout(kwargs.get("timeout", 15))
            return func(*args, **kwargs)

        return inner

    return wrapper


def cache():
    """decorator the define the retry logic of connections tring to send get request"""

    def define_key(self, limit=None, files_types=None):
        key = self.get_chain_name()
        if limit:
            key = key + "_" + str(limit)  # + func.__name__
        if files_types:
            key = key + "_" + ".".join(files_types)

        return key

    def wrapper(func):
        @cached(cache=TTLCache(maxsize=1024, ttl=60), key=define_key)
        def inner(*args, **kwargs):
            return func(*args, **kwargs)

        return inner

    return wrapper


@cached(cache=TTLCache(maxsize=1024, ttl=60))
def get_ip():
    """get the ip of the computer running the code"""
    response = requests.get("https://api64.ipify.org?format=json", timeout=15).json()
    return response["ip"]


@cached(cache=TTLCache(maxsize=1024, ttl=60))
def get_location():
    """get the estimated location of the computer running the code"""
    ip_address = get_ip()
    response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=15).json()
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


@cached(cache=TTLCache(maxsize=1024, ttl=60 * 5))
def get_random_user_agent():
    """get random user agent"""
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:38.0) Gecko/20100101 Firefox/38.0",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0",
        "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0",
        "Mozilla/5.0 (compatible; MSIE 6.0; Windows NT 5.1)",
        "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 2.0.50727)",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:31.0) Gecko/20100101 Firefox/31.0",
        "Opera/9.80 (Windows NT 6.2; Win64; x64) Presto/2.12.388 Version/12.17",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0",
        "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:41.0) Gecko/20100101 Firefox/41.0",
    ]

    index = random.randrange(len(user_agents) - 1)
    return {"User-Agent": str(user_agents[index])}


@url_connection_retry()
def session_with_cookies(url, timeout=15, chain_cookie_name=None):
    """request resource with cookies enabled"""

    session = requests.Session()

    if chain_cookie_name:
        session.cookies = MozillaCookieJar(f"{chain_cookie_name}_cookies.txt")
        try:
            session.cookies.load()
        except FileNotFoundError:
            Logger.info("didn't find cookie file")

    Logger.info(f"On a new Session requesting url: {url}")

    response_content = session.get(url, timeout=timeout)

    if response_content.status_code != 200:
        Logger.info(
            f"On Session, Got status code: {response_content.status_code}"
            f", body is {response_content.text} "
        )
        raise ConnectionError(
            f"response for {url}, returned with status"
            f" {response_content.status_code}"
        )

    if chain_cookie_name and not os.path.exists(f"{chain_cookie_name}_cookies.txt"):
        session.cookies.save()
    return response_content


@url_connection_retry()
def session_and_check_status(url, timeout=15):
    """use a session to load the response and check status"""
    return session_with_cookies(url, timeout=timeout)


def url_retrieve(url, filename):
    # from urllib.request import urlretrieve
    # urlretrieve(url, filename)
    # >>> add here timeout if needed
    """alternative to urllib.request.urlretrieve"""
    with open(filename, "wb") as out_file:
        with contextlib.closing(urllib.request.urlopen(url)) as file:
            block_size = 1024 * 8
            while True:
                block = file.read(block_size)
                if not block:
                    break
                out_file.write(block)
