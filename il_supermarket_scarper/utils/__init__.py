from .files.gzip_utils import (
    extract_xml_from_gz_in_memory,
    extract_if_compressed,
    is_compressed_content,
    validate_gzip_integrity,
    GzipIntegrity,
    GzipStatus,
    GZIP_OK,
    GZIP_TRUNCATED,
    GZIP_CRC_MISMATCH,
    GZIP_NOT_GZIP,
)
from .core.logger import Logger
from .scraping.status import (
    get_output_folder,
    clean_dump_folder,
    summerize_dump_folder_contant,
    _is_saturday_in_israel,
    _is_holiday_in_israel,
    _is_weekend_in_israel,
    _now,
    datetime_in_tlv,
    _testing_now,
    hour_files_expected_to_be_accassible,
)
from .scraping.scraper_status import ScraperStatus
from .files.verified_downloads import VerifiedDownloads
from .files.save_policy import SavePolicy, SaveDecision, should_persist
from .scraping.scraper_status_contract import (
    FileName,
    FolderSizeInfo,
    StartedStatus,
    CollectedStatus,
    DownloadedStatus,
    FailedStatus,
    EstimatedSizeStatus,
    SawStatus,
    VerifiedDownload,
    ScraperStatusOutput,
)
from .files.file_types import FileTypesFilters
from .network.connection import (
    download_connection_retry,
    url_connection_retry,
    disable_when_outside_israel,
    session_with_cookies,
    url_retrieve_to_memory,
    collect_from_ftp,
    fetch_file_from_ftp_to_memory,
    wget_file_to_memory,
    async_url_connection_retry,
)
from .core.loop import execute_in_parallel, multiple_page_aggregtion
from .core.exceptions import RestartSessionError
from .core.retry import retry_files
from .core.validation import is_valid_chain_name, change_xml_encoding
from .scraping.folders_name import DumpFolderNames
from .scraping.deprecated_scrapers import DeprecatedScrapers
from .scraping.status import convert_unit, UnitSize, convert_nl_size_to_bytes, string_to_float
from .scraping.state import FilterState
from .files.file_output import (
    FileOutput,
    DiskFileOutput,
    QueueFileOutput,
    AbstractQueueHandler,
    InMemoryQueueHandler,
    content_sha256,
)
from .scraping.scraper_config import ScraperConfig
from .databases import JsonDataBase, MongoDataBase
from .scraping.scraping_result import ScrapingResult
from .files.file_entry import FileEntry
from .scraping.scraper_status_contract import *
