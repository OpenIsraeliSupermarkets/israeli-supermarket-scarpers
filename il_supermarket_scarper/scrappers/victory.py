import re
from il_supermarket_scarper.engines import Matrix, ApiWebEngine
from il_supermarket_scarper.utils import DumpFolderNames, FileEntry, Logger, FileTypesFilters


class Victory(Matrix):
    """scraper for victory"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.VICTORY,
            chain_hebrew_name="ויקטורי",
            chain_id=["7290696200003", "7290058103393"],
            file_output=file_output,
            status_database=status_database,
        )


class VictoryNewSource(ApiWebEngine):
    """scraper for victory new source using laibcatalog.co.il API"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.VICTORY,
            chain_id=["7290696200003", "7290058103393"],
            url="https://laibcatalog.co.il",
            file_output=file_output,
            status_database=status_database,
        )
        self.chain_hebrew_name = "ויקטורי"

    def get_branches(self, chain_id):
        """Get available branches for a chain ID"""
        return self.get_api_data("/webapi/api/getbranches", {"edi": chain_id})

    def get_files(self, chain_id, branch_number=None):
        """Get available files for a chain ID and optional branch"""
        params = {"edi": chain_id}
        if branch_number is not None:
            params["branchNumber"] = branch_number
        return self.get_api_data("/webapi/api/getfiles", params)

    def get_request_url(self, files_types=None, store_id=None, when_date=None):
        """Generate API requests for getting file lists"""
        requests = []

        for chain_id in self.get_chain_id():
            # Get branches first
            branches = self.get_branches(chain_id)
            Logger.debug(f"Found {len(branches)} branches for chain {chain_id}")

            if store_id is not None:
                # Filter to specific store/branch
                branches = [
                    b for b in branches if str(b.get("number")) == str(store_id)
                ]
                Logger.debug(
                    f"Filtered to {len(branches)} branches for store {store_id}"
                )

            # Get files for each branch (or all if no branch filter)
            if branches:
                for branch in branches:
                    requests.append(
                        {
                            "url": f"{self.url.rstrip('/')}/webapi/api/getfiles?edi={chain_id}",
                            "method": "GET",
                            "chain_id": chain_id,
                            "branch_number": branch.get("number"),
                        }
                    )
            else:
                # No specific branch, get all files
                requests.append(
                    {
                        "url": f"{self.url.rstrip('/')}/webapi/api/getfiles?edi={chain_id}",
                        "method": "GET",
                        "chain_id": chain_id,
                        "branch_number": None,
                    }
                )

        return requests

    def get_data_from_page(self, req_res):
        """Parse the getfiles API response"""
        try:
            data = req_res.json() if hasattr(req_res, "json") else req_res
            Logger.debug(f"Retrieved {len(data)} files from API")
            return data
        except (AttributeError, TypeError) as e:
            Logger.error(f"Failed to parse API response: {e}")
            return []

    async def extract_task_from_entry(self, all_trs):
        """Extract download URLs and metadata from API file entries - async generator."""
        for entry in all_trs:
            try:
                file_name = entry.get("fileName", "")
                if not file_name:
                    continue

                download_url = (
                    f"{self.url.rstrip('/')}/webapi/7290696200003/{file_name}"
                )
                base_name = file_name.split(".")[0]
                file_size_str = entry.get("fileSize", "0 B")
                file_size = self._parse_file_size(file_size_str)

                yield FileEntry(name=base_name, url=download_url, size=file_size)

            except (AttributeError, KeyError, TypeError) as e:
                Logger.warning(f"Error extracting task from entry: {e}")

    def _parse_file_size(self, size_str):
        """Parse file size string like '562.84 KB' to bytes"""
        try:
            if isinstance(size_str, (int, float)):
                return size_str

            size_str = str(size_str).strip()
            match = re.match(r"^([\d.]+)\s*(B|KB|MB|GB)$", size_str, re.IGNORECASE)

            if not match:
                return 0

            number = float(match.group(1))
            unit = match.group(2).upper()

            multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
            return int(number * multipliers.get(unit, 1))

        except (ValueError, AttributeError) as e:
            Logger.debug(f"Failed to parse file size '{size_str}': {e}")
            return 0

    def apply_filter_by_type(self, entries, files_types=None):
        """Filter entries by file type"""
        if not files_types or files_types == FileTypesFilters.all_types():
            return entries

        filtered = []
        type_mapping = {
            FileTypesFilters.STORE_FILE.name: ["store", "stores", "storefull"],
            FileTypesFilters.PRICE_FILE.name: ["price"],
            FileTypesFilters.PROMO_FILE.name: ["promo"],
            FileTypesFilters.PRICE_FULL_FILE.name: ["pricefull"],
            FileTypesFilters.PROMO_FULL_FILE.name: ["promofull"],
        }

        wanted_types = set()
        for file_type in files_types:
            wanted_types.update(type_mapping.get(file_type, []))

        for entry in entries:
            entry_type = entry.get("fileType", "").lower()
            if entry_type in wanted_types:
                filtered.append(entry)

        return filtered
