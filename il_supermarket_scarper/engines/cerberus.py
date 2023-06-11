import os


from il_supermarket_scarper.utils import (
    extract_xml_file_from_gz_file,
    Logger,
    execute_in_event_loop,
    collect_from_ftp,
    fetch_temporary_gz_file_from_ftp,
    retry_files,
)
from .engine import Engine


class Cerberus(Engine):
    """scraper for all Cerberus base site. (seems like can't support historical data)"""

    target_file_extensions = ["xml", "gz"]

    def __init__(
        self,
        chain,
        chain_id,
        folder_name=None,
        ftp_host="url.retail.publishedprices.co.il",
        ftp_path="/",
        ftp_username="",
        ftp_password="",
    ):
        super().__init__(chain, chain_id, folder_name)
        self.ftp_host = ftp_host
        self.ftp_path = ftp_path
        self.ftp_username = ftp_username
        self.ftp_password = ftp_password
        self.ftp_session = False

    @retry_files(num_of_retrys=2)
    def scrape(
        self,
        limit=None,
        files_types=None,
        store_id=None,
        only_latest=False,
        files_names_to_scrape=None,
    ):
        super().scrape(
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            only_latest=only_latest,
        )
        files = self.collect_files_details_from_site(
            limit=limit,
            files_types=files_types,
            filter_null=True,
            filter_zero=True,
            store_id=store_id,
            only_latest=only_latest,
            files_names_to_scrape=files_names_to_scrape,
        )
        self.on_collected_details(files)

        results = execute_in_event_loop(
            self.persist_from_ftp, files, max_workers=self.max_workers
        )
        self.on_download_completed(results=results)
        self.on_scrape_completed(self.get_storage_path())
        return results

    def collect_files_details_from_site(
        self,
        limit=None,
        files_types=None,
        filter_null=False,
        filter_zero=False,
        store_id=None,
        only_latest=False,
        files_names_to_scrape=None,
    ):
        """collect all files to download from the site"""
        files = collect_from_ftp(
            self.ftp_host, self.ftp_username, self.ftp_password, self.ftp_path
        )

        Logger.info(f"Found {len(files)} files")

        if filter_zero:
            files = list(
                filter(lambda x: "0000000000000" not in x, files)
            )  # filter out files
            Logger.info(
                f"After filtering with '0000000000000': Found {len(files)} files"
            )

        if filter_null:
            files = list(filter(lambda x: "NULL" not in x, files))  # filter out files
            Logger.info(f"After filtering with 'NULL': Found {len(files)} files")

        files = list(
            filter(lambda x: x.split(".")[-1] in self.target_file_extensions, files)
        )
        Logger.info(
            f"After filtering by {self.target_file_extensions}: Found {len(files)} files"
        )

        # apply noraml filter
        files = self.apply_limit(
            files,
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            only_latest=only_latest,
            files_names_to_scrape=files_names_to_scrape,
        )
        Logger.info(f"After applying limit: Found {len(files)} files")

        return files

    def persist_from_ftp(self, file_name):
        """download file to hard drive and extract it."""
        downloaded = False
        extract_succefully = False
        restart_and_retry = False
        error = None
        try:
            ext = os.path.splitext(file_name)[1]
            if ext not in [".gz", ".xml"]:
                raise ValueError(f"File {file_name} extension is not .gz or .xml")

            Logger.info(f"Start persisting file {file_name}")
            temporary_gz_file_path = os.path.join(self.storage_path, file_name)

            fetch_temporary_gz_file_from_ftp(
                self.ftp_host,
                self.ftp_username,
                self.ftp_password,
                self.ftp_path,
                temporary_gz_file_path,
            )
            downloaded = True

            if ext == ".gz":
                extract_xml_file_from_gz_file(temporary_gz_file_path)

            Logger.info(f"Done persisting file {file_name}")
            extract_succefully = True
        except Exception as exception:  # pylint: disable=broad-except
            Logger.error(
                f"Error downloading {file_name},extract_succefully={extract_succefully}"
                f",downloaded={downloaded}"
            )
            Logger.error_execption(exception)
            error = str(exception)
            restart_and_retry = True
        finally:
            if ext == ".gz" and os.path.exists(temporary_gz_file_path):
                os.remove(temporary_gz_file_path)

        return {
            "file_name": file_name,
            "downloaded": downloaded,
            "extract_succefully": extract_succefully,
            "restart_and_retry": restart_and_retry,
            "error": error,
        }
