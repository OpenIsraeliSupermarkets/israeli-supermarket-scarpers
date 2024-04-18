from urllib.error import URLError
from http.client import RemoteDisconnected
from http.cookiejar import MozillaCookieJar
from http.cookiejar import LoadError

import contextlib
import ntpath
import os
import time
import socket
import random
from ftplib import FTP_TLS, error_perm
import subprocess
import requests

from playwright.sync_api import sync_playwright
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
    error_perm,
    LoadError,
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


def url_connection_retry(init_timeout=15):
    """decorator the define the retry logic of connections tring to send get request"""

    def wrapper(func):
        @retry(
            exceptions=exceptions,
            tries=4,
            delay=2,
            backoff=2,
            max_delay=5 * 60,
            logger=Logger,
            timeout=init_timeout,
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
    response = requests.get("https://api.ipify.org?format=json", timeout=15).json()
    return response["ip"]


@cached(cache=TTLCache(maxsize=1024, ttl=60))
def get_location():
    """get the estimated location of the computer running the code"""
    ip_address = get_ip()
    response = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=15).json()
    location_data = {
        "ip": ip_address,
        "city": response.get(
            "city",
        ),
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

    if (
        estimated_location["country"] is not None
        and estimated_location["country"] != "Israel"
    ):
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
        filemame = f"{chain_cookie_name}_cookies.txt"
        session.cookies = MozillaCookieJar(filemame)
        try:
            session.cookies.load()
        except FileNotFoundError:
            Logger.info("didn't find cookie file")
        except LoadError as e:
            # there was an issue with reading the file.
            os.remove(filemame)
            raise e

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


def render_webpage(url, extraction):
    """render website with playwrite"""

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_load_state("networkidle")
        content = extraction(page)
        browser.close()
    return content


@url_connection_retry()
def session_and_check_status(url, timeout=15):
    """use a session to load the response and check status"""
    return session_with_cookies(url, timeout=timeout)


def url_retrieve(url, filename, timeout=30):
    # from urllib.request import urlretrieve
    # urlretrieve(url, filename)
    # >>> add here timeout if needed
    """alternative to urllib.request.urlretrieve"""
    # https://gist.github.com/xflr6/f29ed682f23fd27b6a0b1241f244e6c9
    with contextlib.closing(
        requests.get(
            url, stream=True, timeout=timeout, headers={"Accept-Encoding": None}
        )
    ) as _request:
        _request.raise_for_status()
        size = int(_request.headers.get("Content-Length", "-1"))
        read = 0
        with open(filename, "wb") as file:
            for chunk in _request.iter_content(chunk_size=None):
                time.sleep(0.5)
                read += len(chunk)
                file.write(chunk)
                file.flush()

    if size >= 0 and read < size:
        msg = f"retrieval incomplete: got only {read:d} out of {size:d} bytes"
        raise ValueError(msg, (filename, _request.headers))
    # with contextlib.closing(requests.get(url, stream=True, timeout=45)) as context:
    #     context.raise_for_status()
    #     with open(filename, "wb") as file:
    #         for chunk in context.iter_content(chunk_size=8_192):
    #             file.write(chunk)
    # with open(filename, "wb") as out_file:
    #     with contextlib.closing(urllib.request.urlopen(url, timeout=45)) as file:
    #         block_size = 1024 * 8
    #         while True:
    #             block = file.read(block_size)
    #             if not block:
    #                 break
    #             out_file.write(block)
    # import shutil
    # with urllib.request.urlopen(url) as response, open(filename, 'wb') as out_file:
    #     shutil.copyfileobj(response, out_file)


@url_connection_retry(60 * 5)
def collect_from_ftp(ftp_host, ftp_username, ftp_password, ftp_path, timeout=60 * 5):
    """collect all files to download from the site"""
    Logger.info(
        f"Open connection to FTP server with {ftp_host} "
        f", username: {ftp_username} , password: {ftp_password}"
    )
    ftp_session = FTP_TLS(ftp_host, ftp_username, ftp_password, timeout=timeout)
    ftp_session.trust_server_pasv_ipv4_address = True
    ftp_session.set_pasv(True)
    ftp_session.cwd(ftp_path)
    files = ftp_session.nlst()
    ftp_session.quit()
    return files


@download_connection_retry()
def fetch_temporary_gz_file_from_ftp(
    ftp_host, ftp_username, ftp_password, ftp_path, temporary_gz_file_path
):
    """download a file from a cerberus base site."""
    with open(temporary_gz_file_path, "wb") as file_ftp:
        file_name = ntpath.basename(temporary_gz_file_path)
        ftp = FTP_TLS(ftp_host, ftp_username, ftp_password)
        ftp.trust_server_pasv_ipv4_address = True
        ftp.cwd(ftp_path)
        ftp.retrbinary("RETR " + file_name, file_ftp.write)
        ftp.quit()


def wget_file(file_link, file_save_path):
    """use wget to download file"""
    Logger.info(f"trying wget file {file_link} to {file_save_path}.")

    files_parts = file_link.split(".")
    if len(files_parts) < 2 or files_parts[-1] not in ["gz", "xml"]:
        raise ValueError(
            f"wget is not supported for file with unkownen extension {file_link}"
        )
    expected_output_file = f"{file_save_path}.{files_parts[-1]}"
    with subprocess.Popen(
        f"wget --output-document={expected_output_file} {file_link}",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True,
    ) as process:
        std_out, std_err = process.communicate()
    Logger.info(f"Wget stdout {std_out}")
    Logger.info(f"Wget stderr {std_err}")

    if not os.path.exists(expected_output_file):
        Logger.error(f"fils is not exists after wget {file_save_path}")
        raise FileNotFoundError(
            f"File wasn't downloaded with wget,std_err is {std_err}"
        )
    return expected_output_file
