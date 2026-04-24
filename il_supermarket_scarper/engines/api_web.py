import json
import requests
from il_supermarket_scarper.utils import Logger
from il_supermarket_scarper.utils import FileEntry
from il_supermarket_scarper.utils.state import FilterState
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

    def get_api_data(self, endpoint, params=None):
        """Make API call and return JSON response"""
        url = f"{self.url.rstrip('/')}{endpoint}"
        try:
            response = self.session.get(url, params=params)
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
        all_entries = []

        # Get API endpoints to query (async generator)
        requests_to_make = self.get_request_url(
            files_types=files_types, store_id=store_id, when_date=when_date
        )

        # Fetch data from each endpoint
        async for request_info in requests_to_make:
            try:
                response = self.session.get(request_info["url"])
                response.raise_for_status()
                page_data = self.get_data_from_page(response)
                if isinstance(page_data, list):
                    all_entries.extend(page_data)
                else:
                    all_entries.append(page_data)
            except Exception as e:  # pylint: disable=broad-exception-caught
                Logger.error(f"Failed to get data from {request_info['url']}: {e}")

        # Apply filtering if needed
        if hasattr(self, "apply_filter_by_type"):
            all_entries = self.apply_filter_by_type(all_entries, files_types)

        if hasattr(self, "dedupe_api_entries"):
            all_entries = self.dedupe_api_entries(all_entries)

        # Async generator pipeline (same as WebBase / multipage_web)
        extracted_files = self.extract_task_from_entry(all_entries)
        files = self.register_all_saw_files_on_site(extracted_files)

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
