import re
from bs4 import BeautifulSoup
from il_supermarket_scarper.utils import Logger, execute_in_parallel
from il_supermarket_scarper.utils import convert_nl_size_to_bytes, UnitSize
from .engine import Engine


class WebBase(Engine):
    """scrape the file of websites that the only why to download them is via web"""

    def __init__(self, chain, chain_id, url, folder_name=None, max_threads=5):
        super().__init__(chain, chain_id, folder_name, max_threads=max_threads)
        self.url = url
        self.max_retry = 2

    def get_data_from_page(self, req_res):
        """get the file list from a page"""
        soup = BeautifulSoup(req_res.text, features="lxml")
        return soup.find_all("tr")[1:]

    def get_request_url(
        self, files_types=None, store_id=None, when_date=None
    ):  # pylint: disable=unused-argument
        """get all links to collect download links from"""
        return [{"url": self.url, "method": "GET"}]

    def get_file_size_from_entry(self, entry):
        """
        Extract file size from a table row entry.
        Looks for size information in table cells, typically in human-readable format.
        Returns size in bytes, or None if not found.
        """
        try:
            size_bytes = re.search(r"\b\d+(\.\d+)?\s*(KB|MB|GB)\b", entry.text)
            size_bytes = convert_nl_size_to_bytes(
                size_bytes.group(0), to_unit=UnitSize.BYTES
            )
            return size_bytes
        except (AttributeError, TypeError) as e:
            Logger.debug(f"Error extracting file size from entry: {e}")
        return None

    def extract_task_from_entry(self, all_trs):
        """extract download links, file names, and file sizes from page list"""
        download_urls = []
        file_names = []
        file_sizes = []
        for x in all_trs:
            try:
                download_urls.append(self.url + x.a.attrs["href"])
                file_names.append(x.a.attrs["href"].split(".")[0].split("/")[-1])
                file_sizes.append(self.get_file_size_from_entry(x))
            except (AttributeError, KeyError, IndexError, TypeError) as e:
                Logger.warning(f"Error extracting task from entry: {e}")

        return download_urls, file_names, file_sizes

    def apply_limit_zip(
        self,
        file_names,
        download_urls,
        file_sizes=None,
        limit=None,
        files_types=None,
        by_function=lambda x: x[0],
        store_id=None,
        when_date=None,
        files_names_to_scrape=None,
        suppress_exception=False,
        random_selection=False,
    ):
        """apply limit to zip"""
        # Handle both 2-tuple (backward compatibility) and 3-tuple formats
        if file_sizes is None:
            zipped = list(zip(file_names, download_urls))
        else:
            zipped = list(zip(file_names, download_urls, file_sizes))

        ziped = self.apply_limit(
            zipped,
            limit=limit,
            files_types=files_types,
            by_function=by_function,
            store_id=store_id,
            when_date=when_date,
            files_names_to_scrape=files_names_to_scrape,
            suppress_exception=suppress_exception,
            random_selection=random_selection,
        )
        if len(ziped) == 0:
            if file_sizes is None:
                return [], []
            return [], [], []
        return list(zip(*ziped))

    def filter_bad_files_zip(
        self,
        file_names,
        download_urls,
        file_sizes=None,
        filter_null=False,
        filter_zero=False,
        by_function=lambda x: x[0],
    ):
        """apply bad files filtering to zip"""
        # Handle both 2-tuple (backward compatibility) and 3-tuple formats
        if file_sizes is None:
            files = list(zip(file_names, download_urls))
        else:
            files = list(zip(file_names, download_urls, file_sizes))

        files = self.filter_bad_files(
            files,
            filter_null=filter_null,
            filter_zero=filter_zero,
            by_function=by_function,
        )
        if len(files) == 0:
            if file_sizes is None:
                return [], []
            return [], [], []
        return list(zip(*files))

    def collect_files_details_from_site(  # pylint: disable=too-many-locals
        self,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        filter_null=False,
        filter_zero=False,
        files_names_to_scrape=None,
        suppress_exception=False,
        min_size=None,
        max_size=None,
        random_selection=False,
    ):
        """collect all enteris to download from site"""

        urls_to_collect_link_from = self.get_request_url(
            files_types=files_types, store_id=store_id, when_date=when_date
        )
        assert len(urls_to_collect_link_from) > 0, "No pages to scrape"

        all_trs = []
        for url in urls_to_collect_link_from:
            req_res = self.session_with_cookies_by_chain(**url)
            trs = self.get_data_from_page(req_res)
            all_trs.extend(trs)

        Logger.info(f"Found {len(all_trs)} entries")

        download_urls, file_names, file_sizes = self.extract_task_from_entry(all_trs)

        Logger.info(f"Found {len(download_urls)} download urls")

        # Filter by file size if specified
        if min_size is not None or max_size is not None:
            file_names, download_urls, file_sizes = self.filter_by_file_size(
                file_names,
                download_urls,
                file_sizes,
                min_size=min_size,
                max_size=max_size,
            )

        file_names, download_urls, file_sizes = self.filter_bad_files_zip(
            file_names,
            download_urls,
            file_sizes=file_sizes,
            filter_null=filter_null,
            filter_zero=filter_zero,
        )

        Logger.info(f"After filtering bad files: Found {len(download_urls)} files")

        # pylint: disable=duplicate-code
        file_names, download_urls, file_sizes = self.apply_limit_zip(
            file_names,
            download_urls,
            file_sizes=file_sizes,
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            files_names_to_scrape=files_names_to_scrape,
            suppress_exception=suppress_exception,
            random_selection=random_selection,
        )

        Logger.info(f"After applying limit: Found {len(download_urls)} entries")

        return download_urls, file_names

    def _scrape(  # pylint: disable=too-many-locals
        self,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        files_names_to_scrape=None,
        filter_null=False,
        filter_zero=False,
        suppress_exception=False,
        min_size=None,
        max_size=None,
        random_selection=False,
    ):
        """scarpe the files from multipage sites"""
        download_urls, file_names = [], []
        try:
            download_urls, file_names = self.collect_files_details_from_site(
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                when_date=when_date,
                filter_null=filter_null,
                filter_zero=filter_zero,
                files_names_to_scrape=files_names_to_scrape,
                suppress_exception=suppress_exception,
                min_size=min_size,
                max_size=max_size,
                random_selection=random_selection,
            )

            self.on_collected_details(file_names, download_urls)

            Logger.info(f"collected {len(download_urls)} to download.")
            if len(download_urls) > 0:
                results = execute_in_parallel(
                    self.save_and_extract,
                    list(zip(download_urls, file_names)),
                    max_threads=self.max_threads,
                )
            else:
                results = []

            return results
        except Exception as e:  # pylint: disable=broad-except
            self.on_download_fail(e, download_urls=download_urls, file_names=file_names)
            raise e
