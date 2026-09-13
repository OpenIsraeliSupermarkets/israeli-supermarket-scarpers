import re
import urllib.parse
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qs, urlencode

from lxml import html as lxml_html

from il_supermarket_scarper.engines import MultiPageWeb
from il_supermarket_scarper.utils import DumpFolderNames, FileTypesFilters


class Shufersal(MultiPageWeb):
    """scaper for shufersal"""

    utilize_date_param = False

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            url="https://prices.shufersal.co.il/",
            total_page_xpath="""//*[@id="gridContainer"]/table/tfoot/tr/td/a/@href""",
            total_pages_pattern=r"[?&]page=([0-9]+)",
            chain=DumpFolderNames.SHUFERSAL,
            chain_id="7290027600007",
            file_output=file_output,
            status_database=status_database,
            page_argument="page",
        )

    async def get_request_url(
        self, files_types=None, store_id=None, when_date=None
    ):  # pylint: disable=unused-argument
        """Join listing roots without introducing a double slash."""
        for arguments in self.build_params(
            files_types=files_types, store_id=store_id, when_date=when_date
        ):
            yield {
                "url": urljoin(self.url, arguments),
                "method": "GET",
            }

    def get_number_of_pages(self, response):
        """Use the highest page= in the footer, not a[6] (that is the >> skip)."""
        html_body = lxml_html.fromstring(response.content)
        hrefs = html_body.xpath(self.total_page_xpath)
        page_nums = []
        for href in hrefs:
            match = re.search(self.total_pages_pattern, href or "")
            if match:
                page_nums.append(int(match.group(1)))
        if not page_nums:
            return None
        return max(page_nums)

    def _page_url(self, base_url, page_number):
        """Attach page=N with ? or & as appropriate."""
        if page_number <= 1:
            return base_url
        parsed = urlsplit(base_url)
        query = parse_qs(parsed.query, keep_blank_values=True)
        query["page"] = [str(page_number)]
        return urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                urlencode(query, doseq=True),
                parsed.fragment,
            )
        )

    def _pages_to_scrape(self, main_page_request, total_pages):
        """Build page URLs from the listing root (page 1 is the root itself)."""
        if total_pages is None:
            return [main_page_request]
        base_url = main_page_request["url"]
        return [
            {**main_page_request, "url": self._page_url(base_url, page_number)}
            for page_number in range(1, total_pages + 1)
        ]

    def get_file_types_id(self, files_types=None):
        """get the file type id"""
        if files_types is None:
            return ["0"]

        types = []
        for ftype in files_types:
            if ftype == FileTypesFilters.STORE_FILE.name:
                types.append("5")
            if ftype == FileTypesFilters.PRICE_FILE.name:
                types.append("1")
            if ftype == FileTypesFilters.PROMO_FILE.name:
                types.append("3")
            if ftype == FileTypesFilters.PRICE_FULL_FILE.name:
                types.append("2")
            if ftype == FileTypesFilters.PROMO_FULL_FILE.name:
                types.append("4")
        return types

    def build_params(self, files_types=None, store_id=None, when_date=None):
        """build the params for the request"""
        file_type_ids = self.get_file_types_id(files_types)

        urls = []
        for file_type_id in file_type_ids:
            if file_type_id == "0" and not store_id:
                # Default "all" view matches the human portal at /, not catID=0.
                urls.append("")
                continue
            params = {"catID": file_type_id}

            if store_id:
                params["storeId"] = store_id
            urls.append(f"FileObject/UpdateCategory?{urllib.parse.urlencode(params)}")
        return urls
