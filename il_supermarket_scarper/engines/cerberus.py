import datetime
from typing import AsyncGenerator

from il_supermarket_scarper.utils import FileEntry
from il_supermarket_scarper.utils import (
    Logger,
    collect_from_ftp,
    fetch_file_from_ftp_to_memory,
    FileTypesFilters,
    ScrapingResult,
    content_sha256,
    SaveDecision,
)
from il_supermarket_scarper.utils.state import FilterState
from .engine import Engine


class Cerberus(Engine):
    """scraper for all Cerberus base site. (seems like can't support historical data)"""

    target_file_extensions = ["xml", "gz"]
    utilize_date_param = False

    def __init__(
        self,
        chain,
        chain_id,
        ftp_host="url.retail.publishedprices.co.il",
        ftp_path="/",
        ftp_username="",
        ftp_password="",
        max_threads=5,
        file_output=None,
        status_database=None,
    ):
        super().__init__(
            chain,
            chain_id,
            max_threads,
            file_output=file_output,
            status_database=status_database,
        )
        self.ftp_host = ftp_host
        self.ftp_path = ftp_path
        self.ftp_username = ftp_username
        self.ftp_password = ftp_password
        self.ftp_session = False

    async def process_file(self, file_details):
        """Process a single listing FileEntry from Cerberus."""
        entry = file_details

        self.register_collected_file(
            file_name_collected_from_site=entry.name,
            link_collected_from_site=None,
        )

        async for result in self.persist_from_ftp(entry):
            return result

        return ScrapingResult(
            file_entry=entry,
            downloaded=False,
            save_decision=None,
            extract_succefully=False,
            error="No result from persist_from_ftp",
            restart_and_retry=False,
        )

    async def get_type_pattern(self, files_types):
        """get the file type pattern"""
        file_type_mapping = {
            FileTypesFilters.STORE_FILE.name: "store",
            FileTypesFilters.PRICE_FILE.name: "price[0-9]",
            FileTypesFilters.PROMO_FILE.name: "promo[0-9]",
            FileTypesFilters.PRICE_FULL_FILE.name: "pricef",
            FileTypesFilters.PROMO_FULL_FILE.name: "promof",
        }
        if files_types is None or files_types == FileTypesFilters.all_types():
            yield None
            return

        for file_type in files_types:
            if file_type not in file_type_mapping:
                raise ValueError(f"File type {file_type} not supported")
            yield file_type_mapping[file_type]

    async def build_filter_arg(self, store_id=None, when_date=None, files_types=None):
        """build the filter arg for the ftp"""
        date_pattern = None
        if when_date and isinstance(when_date, datetime.datetime):
            date_pattern = when_date.strftime("%Y%m%d")

        async for type_pattern in self.get_type_pattern(files_types):
            output_pattern = []
            if type_pattern:
                output_pattern.append(type_pattern)
            if store_id:
                output_pattern.append(f"{store_id}-")
            if date_pattern:
                output_pattern.append(date_pattern)

            if len(output_pattern) == 0:
                yield "*"
            else:
                yield "*" + "*".join(output_pattern) + "*"

    def is_file_extension_valid(self, file_name):
        """check if the file extension is valid"""
        return file_name.split(".")[-1] in self.target_file_extensions

    async def filter_by_file_extension(
        self, files: AsyncGenerator[FileEntry, None]
    ) -> AsyncGenerator[FileEntry, None]:
        """filter the files by the file extension"""
        async for file in files:
            if not self.is_file_extension_valid(file.name):
                continue
            yield file

    async def collect_files_details_from_site(  # pylint: disable=too-many-locals
        self,
        state: FilterState,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        file_name_regex=None,
        filter_null=False,
        filter_zero=False,
        min_size=None,
        max_size=None,
        random_selection=False,
    ):
        """collect all files to download from the site"""

        async for filter_arg in self.build_filter_arg(store_id, when_date, files_types):
            # Get async generator from FTP
            files_generator = collect_from_ftp(
                self.ftp_host,
                self.ftp_username,
                self.ftp_password,
                self.ftp_path,
                filter_arg,
                fetch_size=min_size is not None or max_size is not None,
            )
            files_generator = self.register_all_saw_files_on_site(files_generator)

            files = self.filter_bad_files(
                files_generator,
                filter_null=filter_null,
                filter_zero=filter_zero,
                by_function=lambda x: x.name,
            )

            files = self.filter_by_file_size(
                files,
                min_size=min_size,
                max_size=max_size,
            )

            files = self.filter_by_file_extension(files)

            # apply normal filter
            async for entry in self.apply_limit(
                state,
                files,
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                when_date=when_date,
                file_name_regex=file_name_regex,
                by_function=lambda x: x.name,
            ):
                yield entry

    async def persist_from_ftp(self, entry):
        """download file to memory and extract it.

        Re-downloads a few times on extract failure (truncated transfer). If the
        FTP SIZE matched and extract still fails, mark ``source_corrupt`` —
        the remote file itself is bad, not our fetch path.
        """
        file_name = entry.name
        downloaded = False
        extract_succefully = False
        restart_and_retry = False
        source_corrupt = False
        error = None
        result = None
        saved_file_name = None
        max_attempts = 3
        try:
            ext = file_name.split(".")[-1] if "." in file_name else ""
            if ext not in ["gz", "xml"]:
                raise ValueError(f"File {file_name} extension is not .gz or .xml")

            Logger.debug(f"Start persisting file {file_name} (in-memory)")

            for attempt in range(1, max_attempts + 1):
                file_content = await fetch_file_from_ftp_to_memory(
                    self.ftp_host,
                    self.ftp_username,
                    self.ftp_password,
                    self.ftp_path,
                    file_name,
                    30,
                )
                downloaded = True

                if ext == "gz":
                    Logger.debug(f"File size is {len(file_content)} bytes.")

                (
                    file_content,
                    extracted_name,
                    extract_succefully,
                    extract_error,
                ) = await self.storage_path.extract_if_compressed(
                    file_content,
                    file_name,
                    getattr(self.storage_path, "extract_gz", True),
                )
                error = extract_error
                if not extract_succefully:
                    Logger.warning(
                        f"Extract failed for {file_name} "
                        f"(attempt {attempt}/{max_attempts}): {error}"
                    )
                    if attempt == max_attempts:
                        source_corrupt = True
                        error = (
                            f"source corrupt after {max_attempts} downloads: "
                            f"{error or 'extract failed'}"
                        )
                        Logger.error(error)
                    continue

                digest = content_sha256(file_content)
                metadata = {
                    "chain": self.chain.value,
                    "chain_id": self.chain_id,
                    "original_filename": file_name,
                    "source": "ftp",
                    "published_at": entry.published_at,
                }
                box = {"result": None}

                async def _persist(
                    content=file_content,
                    name=extracted_name,
                    meta=metadata,
                    dig=digest,
                ):
                    box["result"] = await self.storage_path.save_file(
                        file_link="",
                        file_name=name,
                        file_content=content,
                        metadata=meta,
                        save_decision=SaveDecision.CREATED,
                        content_digest=dig,
                    )

                save_decision = await self.decide_and_persist(
                    extracted_name,
                    digest,
                    entry.published_at,
                    _persist,
                    listing_hash=entry.listing_hash(),
                )
                if box["result"] is not None:
                    result = box["result"]
                    result["save_decision"] = save_decision
                else:
                    result = {
                        "file_name": extracted_name,
                        "saved": True,
                        "extract_successfully": True,
                        "error": None,
                        "content_sha256": digest,
                        "save_decision": save_decision,
                        "metadata": metadata,
                    }
                saved_file_name = extracted_name
                Logger.debug(f"Done persisting file {file_name}")
                break
        except Exception as exception:  # pylint: disable=broad-except
            Logger.error(
                f"Error downloading {file_name},extract_succefully={extract_succefully}"
                f",downloaded={downloaded}"
            )
            Logger.error_execption(exception)
            error = str(exception)
            restart_and_retry = True

        yield ScrapingResult(
            file_entry=entry,
            downloaded=downloaded,
            save_decision=None if result is None else result["save_decision"],
            extract_succefully=extract_succefully,
            content_sha256=None if result is None else result["content_sha256"],
            restart_and_retry=restart_and_retry,
            error=error,
            source_corrupt=source_corrupt,
            saved_file_name=saved_file_name,
        )
