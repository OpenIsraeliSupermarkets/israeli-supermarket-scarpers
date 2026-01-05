import contextlib
import ntpath
import os
import time
import socket
import pickle
import random
import asyncio
import fnmatch
from ftplib import FTP_TLS, error_perm
import subprocess

from http.client import RemoteDisconnected
from http.cookiejar import LoadError
from urllib.error import URLError
from urllib3.exceptions import MaxRetryError, ReadTimeoutError


import requests
from playwright.sync_api import sync_playwright
from requests.exceptions import (
    ReadTimeout,
    ConnectionError as RequestsConnectionError,
    ChunkedEncodingError,
    ConnectTimeout,
)
from .logger import Logger
from .retry import retry
from .file_cache import file_cache


exceptions = (
    URLError,
    RemoteDisconnected,
    ConnectionResetError,
    ConnectTimeout,
    MaxRetryError,
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
        # Store the original requested timeout in a closure variable
        # This will be set by the outer wrapper before retry processes it
        requested_timeout_ref = [init_timeout]

        def outer_wrapper(*args, **kwargs):
            # Capture the timeout from the original call before retry processes it
            original_timeout = kwargs.get("timeout", init_timeout)
            if original_timeout > requested_timeout_ref[0]:
                requested_timeout_ref[0] = original_timeout
            # Now call the retry-decorated function
            return retry_decorated_func(*args, **kwargs)

        @retry(
            exceptions=exceptions,
            tries=4,
            delay=2,
            backoff=2,
            max_delay=5 * 60,
            logger=Logger,
            timeout=init_timeout,
            backoff_timeout=10,
        )
        def retry_decorated_func(*args, **kwargs):
            # Use the higher of retry's timeout or the originally requested timeout
            retry_timeout = kwargs.get("timeout", init_timeout)
            actual_timeout = max(retry_timeout, requested_timeout_ref[0])
            socket.setdefaulttimeout(actual_timeout)
            kwargs["timeout"] = actual_timeout
            return func(*args, **kwargs)

        return outer_wrapper

    return wrapper


def async_url_connection_retry(init_timeout=15):
    """Async decorator for retry logic of connections trying to send requests"""

    def wrapper(func):
        # Store the original requested timeout in a closure variable
        requested_timeout_ref = [init_timeout]

        async def outer_wrapper(*args, **kwargs):
            # Capture the timeout from the original call
            original_timeout = kwargs.get("timeout", init_timeout)
            if original_timeout > requested_timeout_ref[0]:
                requested_timeout_ref[0] = original_timeout

            # Manual retry logic for async functions
            _tries = 4
            _delay = 2
            backoff = 2
            max_delay = 5 * 60

            while _tries:
                try:
                    retry_timeout = kwargs.get("timeout", init_timeout)
                    actual_timeout = max(retry_timeout, requested_timeout_ref[0])
                    socket.setdefaulttimeout(actual_timeout)
                    kwargs["timeout"] = actual_timeout
                    return await func(*args, **kwargs)
                except exceptions as error:
                    _tries -= 1
                    if not _tries:
                        raise

                    if Logger is not None:
                        Logger.warning(
                            "%s, configured timeout %s, retrying in %s seconds",
                            error,
                            actual_timeout,
                            _delay,
                        )
                        Logger.error_execption(error)

                    await asyncio.sleep(_delay)
                    _delay = min(_delay * backoff, max_delay)
                    requested_timeout_ref[0] += 10  # backoff_timeout

            raise ValueError("shouldn't be called!")

        return outer_wrapper

    return wrapper


@file_cache(ttl=60)
def get_ip():
    """get the ip of the computer running the code"""
    response = requests.get("https://api.ipify.org?format=json", timeout=15).json()
    return response["ip"]


@file_cache(ttl=60)
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

    execute = True
    try:
        estimated_location = get_location()
        execute = not (
            estimated_location["country"] is not None
            and estimated_location["country"] != "Israel"
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        Logger.warning(f"error in getting location {str(e)}")

    if execute:
        return function

    Logger.info(f"estimated location is {str(estimated_location)}")
    return _decorator


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


@url_connection_retry(
    init_timeout=60
)  # Increased default to handle slow servers like Shufersal
def session_with_cookies(
    url, timeout=15, chain_cookie_name=None, method="GET", body=None, headers=None
):
    """
    Request resource with cookies enabled.

    Parameters:
    - url: URL to request
    - timeout: Request timeout
    - chain_cookie_name: Optional, name for saving/loading cookies
    - method: HTTP method, defaults to GET
    - body: Data to be sent in the request body (for POST or PUT requests)
    - headers: Optional dict of custom headers to include in the request
    """

    session = requests.Session()
    if chain_cookie_name:

        try:
            with open(chain_cookie_name, "rb") as f:
                session.cookies.update(pickle.load(f))
            # session.cookies.load()
        except FileNotFoundError:
            Logger.debug("Didn't find cookie file")
        except Exception as e:
            # There was an issue with reading the file.
            os.remove(chain_cookie_name)
            raise e

    Logger.debug(
        f"On a new Session requesting url: method={method}, url={url}, body={body}"
    )

    if method == "POST":
        response_content = session.post(
            url, data=body, timeout=timeout, headers=headers
        )
    else:
        response_content = session.get(url, timeout=timeout, headers=headers)

    if response_content.status_code != 200:
        Logger.debug(
            f"On Session, got status code: {response_content.status_code}"
            f", body is {response_content.text} "
        )
        raise ConnectionError(
            f"Response for {url}, returned with status"
            f" {response_content.status_code}"
        )

    if chain_cookie_name and not os.path.exists(chain_cookie_name):
        with open(chain_cookie_name, "wb") as f:
            pickle.dump(session.cookies.get_dict(), f)

    return response_content


def get_from_playwrite(page, extraction_type):
    """get the content from the page with playwrite"""

    if extraction_type == "update_date":
        content = page.locator(
            '//*[@id="content"]/div[1]/div/div/div/div[2]/div[6]/div'
        ).last.inner_text()
    elif extraction_type == "links_name":
        content = page.evaluate(
            """() => {
        const links = Array.from(document.querySelectorAll('a'));
        return links.map(link => link.textContent.trim());
    }"""
        )
    elif extraction_type == "all_text":
        content = page.evaluate(
            """
        () => {
            return document.body.innerText;
        }"""
        )
    else:
        raise ValueError(f"type '{extraction_type}' is not valid.")
    return content


@file_cache(ttl=60)
def render_webpage(url):
    """render website with playwrite"""

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_load_state("domcontentloaded", timeout=60000)
        content = page.content()
        browser.close()
    return content


def get_from_latast_webpage(url, extraction_type):
    """get the content from the page with playwrite"""
    time.sleep(1)
    content = render_webpage(url)
    return get_from_webpage(content, extraction_type)


def get_from_webpage(cached_page, extraction_type):
    """render website with playwrite from file system cache"""

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(cached_page)
        page.wait_for_load_state("domcontentloaded", timeout=60000)
        content = get_from_playwrite(page, extraction_type)
        browser.close()
    return content


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


async def collect_from_ftp(
    ftp_host, ftp_username, ftp_password, ftp_path, arg=None, timeout=60 * 5
):
    """Async generator: yields (filename, size) tuples from the FTP server"""
    Logger.info(
        f"Open async connection to FTP server with {ftp_host} "
        f", username: {ftp_username} , password: {ftp_password}"
    )

    def _sync_ftp_list():  # pylint: disable=too-many-branches
        """Synchronous FTP listing using FTP_TLS - returns a list"""
        ftp = FTP_TLS(ftp_host, ftp_username, ftp_password, timeout=timeout)
        ftp.trust_server_pasv_ipv4_address = True
        try:
            ftp.cwd(ftp_path)

            # Use MLSD for detailed file info if available, fall back to NLST + SIZE
            files_with_sizes = []
            try:
                # MLSD provides detailed info including size
                all_entries = list(ftp.mlsd())

                for name, facts in all_entries:
                    if facts.get("type") == "file":
                        size_str = facts.get("size")
                        try:
                            size = int(size_str) if size_str else None
                        except (ValueError, TypeError):
                            size = None

                        # Apply glob filter if arg is provided (case-insensitive)
                        if arg is None or fnmatch.fnmatch(name.lower(), arg.lower()):
                            files_with_sizes.append((name, size))
                    elif facts.get("type") in ["dir", "cdir", "pdir"]:
                        # Skip directories
                        pass
                    else:
                        # Unknown type - include if matches filter (case-insensitive)
                        if arg is None or fnmatch.fnmatch(name.lower(), arg.lower()):
                            files_with_sizes.append((name, None))
            except error_perm:
                # MLSD not supported, fall back to NLST
                if arg:
                    file_list = ftp.nlst(arg)
                else:
                    file_list = ftp.nlst()

                # Get size for each file
                for filename in file_list:
                    try:
                        ftp.voidcmd("TYPE I")  # Set binary mode
                        size = ftp.size(filename)
                    except error_perm:
                        size = None
                    files_with_sizes.append((filename, size))

            return files_with_sizes
        finally:
            try:
                ftp.quit()
            except Exception:  # pylint: disable=broad-exception-caught
                ftp.close()

    # Run synchronous FTP operations in a thread pool and get the list
    files_list = await asyncio.to_thread(_sync_ftp_list)

    # Yield each file as an async generator
    for filename, size in files_list:
        yield (filename, size)


async def fetch_temporary_gz_file_from_ftp(
    ftp_host, ftp_username, ftp_password, ftp_path, temporary_gz_file_path, timeout=15
):
    """download a file from a cerberus base site."""
    Logger.info(
        f"Downloading file from FTP server with {ftp_host} "
        f", username: {ftp_username} , password: {ftp_password}"
    )

    def _sync_ftp_download(ftp_timeout):
        """Synchronous FTP download using FTP_TLS"""
        socket.setdefaulttimeout(ftp_timeout)
        with open(temporary_gz_file_path, "wb") as file_ftp:
            file_name = ntpath.basename(temporary_gz_file_path)
            ftp = FTP_TLS(ftp_host, ftp_username, ftp_password, timeout=ftp_timeout)
            ftp.trust_server_pasv_ipv4_address = True
            ftp.cwd(ftp_path)
            ftp.retrbinary("RETR " + file_name, file_ftp.write)
            ftp.quit()

    # Manual retry logic for async functions (matching download_connection_retry parameters)
    _tries = 8
    _delay = 2
    backoff = 2
    max_delay = 5 * 60
    _timeout = timeout
    backoff_timeout = 5

    while _tries:
        try:
            await asyncio.to_thread(_sync_ftp_download, _timeout)
            return
        except exceptions as error:
            _tries -= 1
            if not _tries:
                raise

            if Logger is not None:
                Logger.warning(
                    "%s, configured timeout %s, retrying in %s seconds",
                    error,
                    _timeout,
                    _delay,
                )
                Logger.error_execption(error)

            await asyncio.sleep(_delay)
            _delay = min(_delay * backoff, max_delay)
            _timeout += backoff_timeout

    raise ValueError("shouldn't be called!")


def wget_file(file_link, file_save_path):
    """use wget to download file"""
    Logger.debug(f"trying wget file {file_link} to {file_save_path}.")

    with subprocess.Popen(
        f"wget --output-document={file_save_path} '{file_link}'",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True,
    ) as process:
        std_out, std_err = process.communicate()
    Logger.debug(f"Wget stdout {std_out}")
    Logger.debug(f"Wget stderr {std_err}")

    if not os.path.exists(file_save_path):
        Logger.error(f"fils is not exists after wget {file_save_path}")
        raise FileNotFoundError(
            f"File wasn't downloaded with wget,std_err is {std_err}"
        )

    # wget will create file always, so we need to check if there was an error
    # example for validate case is collecting start and
    # the file is removed before downloading (change of hour)
    if "ERROR 403" in std_err or "ERROR 404" in std_err:
        if os.path.exists(file_save_path):
            os.remove(file_save_path)
        Logger.error(f"Got error {std_err} while downloading {file_link}")
        raise FileNotFoundError(
            f"File wan't found in the remote, possibly removed between "
            f"collection and download, std_err is {std_err}"
        )
    return file_save_path
