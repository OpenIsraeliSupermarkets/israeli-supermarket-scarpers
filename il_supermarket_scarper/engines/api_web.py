import json
import requests
from il_supermarket_scarper.utils import (
    Logger,
)
from .web import WebBase


class ApiWebEngine(WebBase):
    """Engine for API-based scrapers that work with JSON endpoints"""

    def __init__(self, chain, chain_id, url, folder_name=None, max_threads=5):
        super().__init__(chain, chain_id, url, folder_name, max_threads)
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

    def get_request_url(self, files_types=None, store_id=None, when_date=None):
        """Get API endpoints to query - to be overridden by subclasses"""
        return []

    def get_data_from_page(self, req_res):
        """Parse API response - to be overridden by subclasses"""
        try:
            return (
                req_res.json() if hasattr(req_res, "json") else json.loads(req_res.text)
            )
        except (json.JSONDecodeError, AttributeError) as e:
            Logger.error(f"Failed to parse API response: {e}")
            return []

    def extract_task_from_entry(self, all_trs):
        """Extract download tasks from API data - to be overridden by subclasses"""
        download_urls = []
        file_names = []
        file_sizes = []

        for entry in all_trs:
            try:
                # Basic implementation - subclasses should override
                if isinstance(entry, dict):
                    file_name = entry.get(
                        "fileName", entry.get("filename", entry.get("name", ""))
                    )
                    if file_name:
                        download_urls.append(
                            f"{self.url.rstrip('/')}/download/{file_name}"
                        )
                        file_names.append(file_name.split(".")[0])
                        file_sizes.append(entry.get("fileSize", entry.get("size", 0)))
            except (AttributeError, KeyError, TypeError) as e:
                Logger.warning(f"Error extracting task from entry: {e}")

        return download_urls, file_names, file_sizes

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
        """Override WebBase to collect file details from API endpoints instead of HTML pages"""
        all_entries = []

        # Get API endpoints to query
        requests_to_make = self.get_request_url(
            files_types=files_types, store_id=store_id, when_date=when_date
        )

        # Fetch data from each endpoint
        for request_info in requests_to_make:
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
                if not suppress_exception:
                    raise

        # Apply filtering if needed
        if hasattr(self, "apply_filter_by_type"):
            all_entries = self.apply_filter_by_type(all_entries, files_types)

        # Extract download tasks
        download_urls, file_names, file_sizes = self.extract_task_from_entry(
            all_entries
        )

        # Apply other filters similar to WebBase
        file_names, download_urls, file_sizes = self.apply_limit_zip(
            file_names,
            download_urls,
            file_sizes,
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            files_names_to_scrape=files_names_to_scrape,
            suppress_exception=suppress_exception,
            random_selection=random_selection,
        )

        return download_urls, file_names
