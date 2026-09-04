import asyncio
import json
import requests
from il_supermarket_scarper.utils import Logger
from il_supermarket_scarper.utils import FileEntry
from il_supermarket_scarper.utils.state import FilterState
from il_supermarket_scarper.utils.async_work import stream_as_completed
from .web import WebBase


class ApiWebEngine(WebBase):
    """Engine for API-based scrapers that work with JSON endpoints"""

    def __init__(
        self,
        chain,
        chain_id,
        url,
        file_output=None,
        status_database=None,
        max_threads=5,
    ):
        super().__init__(
            chain,
            chain_id,
            url,
            max_threads=max_threads,
            file_output=file_output,
            status_database=status_database,
        )
        self.session = requests.Session()

    def get_api_data(self, endpoint, params=None, timeout=30):
        """Make API call and return JSON response"""
        url = f"{self.url.rstrip('/')}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            Logger.error(f"API request failed: {e}")
            return []
        except json.JSONDecodeError as e:
            Logger.error(f"Failed to parse JSON response: {e}")
            return []

    async def get_request_url(self, files_types=None, store_id=None, when_date=None):
        """get API endpoints to query"""
        yield

    def get_data_from_page(self, req_res):
        """Parse API response - to be overridden by subclasses"""
        try:
            return (
                req_res.json() if hasattr(req_res, "json") else json.loads(req_res.text)
            )
        except (json.JSONDecodeError, AttributeError) as e:
            Logger.error(f"Failed to parse API response: {e}")
            return []

    def _fetch_entries_for_request(self, request_info):
        """Sync fetch of one listing endpoint (run in a worker thread)."""
        try:
            timeout = request_info.get("timeout", 30)
            response = self.session.get(request_info["url"], timeout=timeout)
            response.raise_for_status()
            page_data = self.get_data_from_page(response)
            if isinstance(page_data, list):
                return page_data
            return [page_data]
        except Exception as e:  # pylint: disable=broad-exception-caught
            Logger.error(f"Failed to get data from {request_info['url']}: {e}")
            return []

    @staticmethod
    def _entry_filename(entry):
        """Best-effort filename key for streaming dedupe."""
        if not isinstance(entry, dict):
            return None
        return entry.get("fileName") or entry.get("filename") or entry.get("name")

    def _dedupe_streaming_entries(self, entries, seen_names):
        """Drop duplicate API filenames; keep non-dict entries as-is."""
        deduped = []
        for entry in entries:
            filename = self._entry_filename(entry)
            if not filename:
                if not isinstance(entry, dict):
                    deduped.append(entry)
                continue
            if filename in seen_names:
                continue
            seen_names.add(filename)
            deduped.append(entry)
        return deduped

    def _filter_streamed_entries(self, entries, files_types, seen_names):
        """Apply optional type filter and streaming dedupe to one batch."""
        if hasattr(self, "apply_filter_by_type"):
            entries = self.apply_filter_by_type(entries, files_types)
        if hasattr(self, "dedupe_api_entries"):
            entries = self._dedupe_streaming_entries(entries, seen_names)
        return entries

    async def extract_task_from_entry(self, all_trs):
        """Extract download tasks from API data"""
        for entry in all_trs:
            try:
                if isinstance(entry, dict):
                    file_name = entry.get(
                        "fileName", entry.get("filename", entry.get("name", ""))
                    )
                    if file_name:
                        url = f"{self.url.rstrip('/')}/download/{file_name}"
                        name = file_name.split(".")[0]
                        size = entry.get("fileSize", entry.get("size", 0))
                        yield FileEntry(name=name, url=url, size=size)
            except (AttributeError, KeyError, TypeError) as e:
                Logger.warning(f"Error extracting task from entry: {e}")

    async def _stream_api_file_entries(
        self, files_types=None, store_id=None, when_date=None
    ):
        """Yield FileEntry objects as each listing request completes."""
        requests_to_make = self.get_request_url(
            files_types=files_types, store_id=store_id, when_date=when_date
        )
        seen_names = set()

        async def fetch_files(request_info):
            raw = await asyncio.to_thread(
                self._fetch_entries_for_request, request_info
            )
            entries = self._filter_streamed_entries(raw, files_types, seen_names)
            extracted = []
            async for file_entry in self.extract_task_from_entry(entries):
                extracted.append(file_entry)
            return extracted

        async for file_entry in stream_as_completed(
            requests_to_make,
            fetch_files,
            max(1, self.max_threads),
            source_error_prefix="Error getting API listing URL",
            work_error_prefix="Error listing files from API",
        ):
            yield file_entry

    async def collect_files_details_from_site(  # pylint: disable=too-many-locals
        self,
        state: FilterState,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        files_names_to_scrape=None,
        filter_null=False,
        filter_zero=False,
        min_size=None,
        max_size=None,
        random_selection=False,
    ):
        """collect file details from API endpoints"""
        listing = self._stream_api_file_entries(
            files_types=files_types, store_id=store_id, when_date=when_date
        )
        try:
            files = self.register_all_saw_files_on_site(listing)

            if min_size is not None or max_size is not None:
                filtered_files = self.filter_by_file_size(
                    files, min_size=min_size, max_size=max_size
                )
            else:
                filtered_files = files

            bad_files_filtered = self.filter_bad_files(
                filtered_files,
                filter_null=filter_null,
                filter_zero=filter_zero,
                by_function=lambda x: x.name,
            )

            async for entry in self.apply_limit(
                state,
                bad_files_filtered,
                limit=limit,
                files_types=files_types,
                by_function=lambda x: x.name,
                store_id=store_id,
                when_date=when_date,
                files_names_to_scrape=files_names_to_scrape,
                random_selection=random_selection,
            ):
                yield entry.url, entry.name
        finally:
            await listing.aclose()
