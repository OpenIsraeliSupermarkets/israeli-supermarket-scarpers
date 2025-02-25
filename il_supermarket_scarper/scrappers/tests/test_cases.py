# pylint: disable=too-many-statements
import unittest
import tempfile
import re
import os
import uuid
import xml.etree.ElementTree as ET
from lxml import etree
from il_supermarket_scarper.utils import (
    FileTypesFilters,
    Logger,
    DumpFolderNames,
    _testing_now,
    change_xml_encoding,
)
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.scraper_stability import ScraperStability


def make_test_case(scraper_enum, store_id):
    """create test suite for scraper"""

    class TestScapers(unittest.TestCase):
        """class with all the tests for scraper"""

        def __init__(self, name) -> None:
            super().__init__(name)
            self.scraper_enum = scraper_enum
            self.folder_name = "temp"

        def _delete_folder_and_sub_folder(self, download_path):
            """delete a folder and all sub-folder"""
            files_found = os.listdir(download_path)
            for file in files_found:
                file_path = os.path.join(download_path, file)
                if os.path.isdir(file_path):
                    self._delete_folder_and_sub_folder(file_path)
                    os.rmdir(file_path)
                else:
                    os.remove(file_path)

        def _delete_download_folder(self, download_path):
            """delete the download folder"""
            if os.path.isdir(download_path):
                self._delete_folder_and_sub_folder(download_path)
                os.removedirs(download_path)

        def _make_sure_filter_work(
            self,
            files_found,
            file_type=None,
            limit=None,
            store_id=None,
            when_date=None,
        ):
            """make sure the file type filter works"""
            # make sure the file type is applied
            if file_type:
                filtered_files = 0
                for f_type in file_type:
                    filtered_files += len(FileTypesFilters.filter(f_type, files_found))
                assert len(files_found) == filtered_files

            # check the store id is applied
            if store_id:
                for file in files_found:
                    assert re.compile(rf"-0*{store_id}-").search(file)

            # check the date time stamp is applied
            if when_date:
                for file in files_found:
                    assert (
                        when_date.strftime("%Y%m%d") in file
                    ), f"{when_date} not in {file}"

            # check limit
            assert (
                limit is None or len(files_found) == limit
            ), f""" Found {files_found} f"files but should be {limit}"""

        def _make_sure_file_contain_chain_ids(self, chain_ids, file):
            """make sure the scraper download only the chain id"""
            found_chain_id = False
            for possible_chain_ids in chain_ids:
                if possible_chain_ids in file:
                    found_chain_id = True
            assert found_chain_id, f"should be one of {chain_ids} but {file}"

        def _make_sure_file_extension_is_xml(self, file_name):
            """make sure the file extension is xml"""
            file_ext = file_name.split(".")[-1]
            assert file_ext == "xml", f" should be xml but {file_ext}, file:{file_name}"

        def _try_to_recover_xml(self, file_path):
            """try to recover the xml"""
            parser = etree.XMLParser(recover=True, encoding="utf-8")
            with open(file_path, "rb") as f:
                tree = etree.parse(f, parser)
            fixed_xml = etree.tostring(
                tree, pretty_print=True, encoding="utf-8"
            ).decode("utf-8")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_xml)

        def _make_sure_file_is_xml_readable(self, full_file_path):
            """Ensure the file is a valid XML and readable."""
            try:
                ET.parse(full_file_path)
            except ET.ParseError:
                try:
                    self._try_to_recover_xml(full_file_path)
                    ET.parse(full_file_path)
                except ET.ParseError:
                    change_xml_encoding(full_file_path)
                    ET.parse(full_file_path)

        def _clean_scarpe_delete(
            self,
            scraper_enum,
            store_id=None,
            limit=None,
            file_type=None,
            when_date=None,
        ):
            with tempfile.TemporaryDirectory() as tmpdirname:
                self.__clean_scarpe_delete(
                    scraper_enum=scraper_enum,
                    dump_path=tmpdirname,
                    store_id=store_id,
                    limit=limit,
                    file_type=file_type,
                    when_date=when_date,
                )

        def __clean_scarpe_delete(
            self,
            scraper_enum,
            dump_path="temp",
            store_id=None,
            limit=None,
            file_type=None,
            when_date=None,
        ):
            self._delete_download_folder(dump_path)
            os.makedirs(dump_path)
            init_scraper_function = ScraperFactory.get(scraper_enum)

            if init_scraper_function is None:
                Logger.warning(f"{scraper_enum} is disabled.")
            else:
                try:
                    scraper = init_scraper_function(folder_name=dump_path)

                    kwarg = {
                        "limit": limit,
                        "files_types": file_type,
                        "store_id": store_id,
                        "when_date": when_date,
                        "filter_null": True,
                        "filter_zero": True,
                        "suppress_exception": True,
                    }

                    scraper.scrape(**kwarg)

                    files_found = os.listdir(dump_path)
                    assert (
                        len(files_found) == 2
                    ), "only one folder should exists and the status folder"
                    assert DumpFolderNames[scraper_enum.name].value in files_found

                    download_path = os.path.join(
                        dump_path, DumpFolderNames[scraper_enum.name].value
                    )
                    files_found = os.listdir(download_path)

                    if not ScraperStability.is_validate_scraper_found_no_files(
                        scraper_enum.name,
                        limit=limit,
                        files_types=file_type,
                        store_id=store_id,
                        when_date=when_date,
                        utilize_date_param=scraper_enum.value.utilize_date_param,
                    ):
                        self._make_sure_filter_work(
                            files_found,
                            file_type=file_type,
                            limit=limit,
                            store_id=store_id,
                            when_date=when_date,
                        )

                    for file in files_found:
                        self._make_sure_file_contain_chain_ids(
                            scraper.get_chain_id(), file
                        )
                        self._make_sure_file_extension_is_xml(file)

                        self._make_sure_file_is_xml_readable(
                            os.path.join(download_path, file)
                        )
                finally:
                    self._delete_download_folder(dump_path)

        def _get_temp_folder(self):
            """get a temp folder to download the files into"""
            return self.folder_name + str(uuid.uuid4().hex)

        def test_scrape_one(self):
            """scrape one file and make sure it exists"""
            self._clean_scarpe_delete(scraper_enum, limit=1)

        def test_scrape_three(self):
            """scrape three file and make sure they exists"""
            self._clean_scarpe_delete(scraper_enum, limit=3)

        def test_scrape_promo(self):
            """scrape one promo file and make sure it exists"""
            self._clean_scarpe_delete(
                scraper_enum,
                limit=1,
                file_type=FileTypesFilters.only_promo(),
            )

        def test_scrape_store(self):
            """scrape one store file and make sure it exists"""
            self._clean_scarpe_delete(
                scraper_enum, limit=1, file_type=FileTypesFilters.only_store()
            )

        def test_scrape_price(self):
            """scrape one price file and make sure it exists"""
            self._clean_scarpe_delete(
                scraper_enum, limit=1, file_type=FileTypesFilters.only_price()
            )

        def test_scrape_file_from_single_store(self):
            """test fetching only files from a ceriten store"""
            self._clean_scarpe_delete(scraper_enum, store_id=store_id, limit=1)

        def test_scrape_file_today(self):
            """test fetching file from today"""
            self._clean_scarpe_delete(scraper_enum, when_date=_testing_now(), limit=1)

    return TestScapers
