"""Tests for Shufersal last-page detection and page URL joining."""

import tempfile
import unittest
from unittest.mock import MagicMock

from il_supermarket_scarper.scrappers.shufersal import Shufersal
from il_supermarket_scarper.utils import DiskFileOutput, FileTypesFilters


def _pager_html(*hrefs):
    links = "".join(f'<a href="{href}">{label}</a>' for href, label in hrefs)
    return f"""
    <div id="gridContainer">
      <table>
        <tbody><tr><td></td><td></td><td></td><td></td><td></td><td></td>
        <td>file</td></tr></tbody>
        <tfoot><tr><td>{links}</td></tr></tfoot>
      </table>
    </div>
    """


class TestShufersalPagination(unittest.TestCase):
    """Verify Shufersal uses the highest footer page=, not a[6]/>> alone."""

    def test_get_number_of_pages_uses_max_footer_page(self):
        """>> jump (a[6]) must not win if a later numeric link is higher."""
        html = _pager_html(
            ("/?page=2", "2"),
            ("/?page=3", "3"),
            ("/?page=4", "4"),
            ("/?page=5", "5"),
            ("/?page=2", ">"),
            ("/?page=86", ">>"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            scraper = Shufersal(file_output=DiskFileOutput(storage_path=tmp))
            response = MagicMock(content=html.encode())
            self.assertEqual(scraper.get_number_of_pages(response), 86)

    def test_pages_to_scrape_uses_query_page_on_root(self):
        """Root listing page 2 is /?page=2, not /&page=2."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = Shufersal(file_output=DiskFileOutput(storage_path=tmp))
            pages = scraper._pages_to_scrape(  # pylint: disable=protected-access
                {"url": "https://prices.shufersal.co.il/", "method": "GET"},
                3,
            )
            self.assertEqual(
                [page["url"] for page in pages],
                [
                    "https://prices.shufersal.co.il/",
                    "https://prices.shufersal.co.il/?page=2",
                    "https://prices.shufersal.co.il/?page=3",
                ],
            )

    def test_pages_to_scrape_appends_page_on_category_url(self):
        """Category roots already have a query string; page uses &."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = Shufersal(file_output=DiskFileOutput(storage_path=tmp))
            pages = scraper._pages_to_scrape(  # pylint: disable=protected-access
                {
                    "url": (
                        "https://prices.shufersal.co.il/FileObject/"
                        "UpdateCategory?catID=1"
                    ),
                    "method": "GET",
                },
                2,
            )
            self.assertEqual(
                pages[1]["url"],
                "https://prices.shufersal.co.il/FileObject/"
                "UpdateCategory?catID=1&page=2",
            )

    def test_build_params_uses_root_for_all_types(self):
        """Unfiltered listing should land on / like the human UI."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = Shufersal(file_output=DiskFileOutput(storage_path=tmp))
            self.assertEqual(scraper.build_params(), [""])

    def test_build_params_keeps_category_url_for_filtered_types(self):
        """Typed filters should still use UpdateCategory endpoints."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = Shufersal(file_output=DiskFileOutput(storage_path=tmp))
            params = scraper.build_params(
                files_types=[FileTypesFilters.PRICE_FILE.name]
            )
            self.assertEqual(params, ["FileObject/UpdateCategory?catID=1"])
