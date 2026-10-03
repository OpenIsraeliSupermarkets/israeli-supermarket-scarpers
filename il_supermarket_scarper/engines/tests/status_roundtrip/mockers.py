"""Network mockers: each one patches an engine family's I/O seam and serves data.

Use as a context manager around scraper construction and ``scrape()``.
"""

# pylint: disable=missing-function-docstring,too-few-public-methods,unused-argument

import asyncio
import gzip
import json
from abc import ABC, abstractmethod
from contextlib import ExitStack
from unittest.mock import patch

import requests

from il_supermarket_scarper.utils import FileEntry


class Mocker(ABC):
    """Base mocker: fast retries, plus whatever ``patches()`` adds."""

    FILE_NAMES = [
        "PriceFull7290000000001-001-202410070010",
        "PriceFull7290000000001-002-202410070010",
    ]
    FILE_BYTES = gzip.compress(b"<Root><Items><Item>1</Item></Items></Root>")
    FILES_HOST = "http://files.test"

    def __init__(self, download_error=False):
        self.download_error = download_error
        self._stack = ExitStack()

    def __enter__(self):
        real_sleep = asyncio.sleep

        async def fast_sleep(delay, *args, **kwargs):  # retries must not wait
            await real_sleep(0)

        self._stack.__enter__()
        self._stack.enter_context(patch("asyncio.sleep", fast_sleep))
        for mock_patch in self.patches():
            self._stack.enter_context(mock_patch)
        return self

    def __exit__(self, *exc_info):
        return self._stack.__exit__(*exc_info)

    @abstractmethod
    def patches(self):
        """The ``unittest.mock`` patches that cut the network."""


class HttpMocker(Mocker):
    """Patches ``requests`` and serves ``routes()`` listings plus file bytes."""

    class Response:
        """Minimal ``requests.Response`` stand-in."""

        def __init__(self, body=b"", status_code=200):
            self.content = body if isinstance(body, bytes) else body.encode("utf-8")
            self.status_code = status_code
            self.headers = {"Content-Length": str(len(self.content))}

        @property
        def text(self):
            return self.content.decode("utf-8", errors="replace")

        def json(self):
            return json.loads(self.text)

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.exceptions.HTTPError(str(self.status_code))

        def iter_content(self, chunk_size=8192):
            yield self.content

        def close(self):
            """Needed by ``contextlib.closing``."""

    class Cookies:
        """Picklable cookie jar."""

        def __init__(self):
            self._jar = {}

        def update(self, other):
            self._jar.update(other)

        def get_dict(self):
            return dict(self._jar)

    def routes(self):
        """List of ``(url fragment, body)``; the first fragment in the URL wins."""
        return []

    def handle(self, url):
        # Bina resolves "Download.aspx?FileNm=x.gz" through a listing-style route
        if url.endswith((".gz", ".xml")) and "Download.aspx" not in url:
            if self.download_error:
                raise requests.exceptions.ConnectionError(f"cannot reach {url}")
            return self.Response(self.FILE_BYTES)
        for fragment, body in self.routes():
            if fragment in url:
                return self.Response(body)
        return self.Response(b"not found", status_code=404)

    def patches(self):
        mocker = self

        class Session:
            """``requests.Session`` stand-in routed through the mocker."""

            def __init__(self, *args, **kwargs):
                self.cookies = mocker.Cookies()
                self.headers = {}

            def get(self, url, **kwargs):
                return mocker.handle(url)

            def post(self, url, data=None, **kwargs):
                return mocker.handle(url)

        return [
            patch("requests.Session", Session),
            patch("requests.get", lambda url, **kwargs: mocker.handle(url)),
            patch("shutil.which", return_value=None),  # no wget fallback
        ]


class BinaMocker(HttpMocker):
    """Bina: JSON listing plus the Download.aspx SPath redirect."""

    def routes(self):
        listing = [
            {"FileNm": f"{n}.gz", "DateFile": "10:00 07/10/2024"}
            for n in self.FILE_NAMES
        ]
        resolve = [{"SPath": f"{self.FILES_HOST}/{self.FILE_NAMES[0]}.gz"}]
        return [
            ("MainIO_Hok", json.dumps(listing)),
            ("Download.aspx", json.dumps(resolve)),
        ]


class MatrixMocker(HttpMocker):
    """Matrix: HTML table whose rows carry the chain name."""

    def routes(self):
        rows = "".join(
            f'<tr><td>ח. כהן</td><td><a href="{self.FILES_HOST}/{n}.gz">dl</a></td></tr>'
            for n in self.FILE_NAMES
        )
        html = f"<html><body><table><tr><th>h</th></tr>{rows}</table></body></html>"
        return [("laibcatalog.co.il/", html)]


class PublishPriceMocker(HttpMocker):
    """PublishPrice: file list hard-coded in a page script."""

    def routes(self):
        files = json.dumps(
            [
                {"name": f"{n}.gz", "size": 100, "modified": "10:00 07-10-2024"}
                for n in self.FILE_NAMES
            ]
        )
        html = (
            "<html><body><script>\n"
            "const path = '20241007';\n"
            f"const files = {files}\n"
            "const chains = []\n"
            "</script><script>var a = 1;</script></body></html>"
        )
        return [("carrefour.co.il", html)]


class MultiPageMocker(HttpMocker):
    """MultiPageWeb: single-page gridContainer table."""

    def routes(self):
        rows = "".join(
            "<tr>"
            f'<td><a href="{self.FILES_HOST}/{n}.gz">dl</a></td>'
            "<td>10/07/2024 10:00:00 AM</td><td>1 KB</td></tr>"
            for n in self.FILE_NAMES
        )
        html = (
            '<html><body><div id="gridContainer"><table><tbody>'
            f"{rows}</tbody></table></div></body></html>"
        )
        return [("shufersal.co.il", html)]


class ApiMocker(HttpMocker):
    """ApiWebEngine: getbranches and getfiles JSON endpoints."""

    def routes(self):
        branches = [{"branchNumber": 1}]
        files = [
            {
                "fileName": f"{n}.gz",
                "fileSize": "1 KB",
                "fileDate": "2024-10-07 10:00:00",
            }
            for n in self.FILE_NAMES
        ]
        return [
            ("getbranches", json.dumps(branches)),
            ("getfiles", json.dumps(files)),
        ]


class PlainWebMocker(HttpMocker):
    """Plain WebBase: a JSON name/url/date listing."""

    def routes(self):
        listing = [
            {
                "name": n,
                "url": f"{self.FILES_HOST}/{n}.gz",
                "date": "2024-10-07 10:00:00",
            }
            for n in self.FILE_NAMES
        ]
        return [("list-files", json.dumps(listing))]


class FtpMocker(Mocker):
    """Cerberus imports its FTP helpers by name, so patch that namespace."""

    MODULE = "il_supermarket_scarper.engines.cerberus"

    def patches(self):
        mocker = self

        async def collect(*args, **kwargs):
            for name in mocker.FILE_NAMES:
                yield FileEntry(
                    name=f"{name}.gz", url=None, size=len(mocker.FILE_BYTES)
                )

        async def fetch(*args, **kwargs):
            if mocker.download_error:
                raise ConnectionError("ftp download failed")
            return mocker.FILE_BYTES

        return [
            patch(f"{self.MODULE}.collect_from_ftp", collect),
            patch(f"{self.MODULE}.fetch_file_from_ftp_to_memory", fetch),
        ]
