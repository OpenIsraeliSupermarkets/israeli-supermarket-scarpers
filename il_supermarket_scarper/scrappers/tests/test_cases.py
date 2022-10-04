import unittest
import os
import uuid
from il_supermarket_scarper.utils import FileTypesFilters


def make_test_case(init_scraper_function):
    """create test suite for scraper"""

    class TestScapers(unittest.TestCase):
        """class with all the tests for scraper"""

        def __init__(self, name) -> None:
            super().__init__(name)
            self.init_scraper_function = init_scraper_function
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

        def _make_sure_filter_work(self, files_found, file_type=None, limit=None):
            """make sure the file type filter works"""
            if file_type:
                filtered_files = 0
                for f_type in file_type:
                    filtered_files += len(FileTypesFilters.filter(f_type, files_found))
                assert len(files_found) == filtered_files

            assert (
                not limit or len(files_found) == limit
            ), f""" Found {files_found}
                                                                f"files but should be {limit}"""

        def _make_sure_file_contain_chain_ids(self, chain_ids, file):
            """make sure the scraper download only the chain id"""
            for possible_chain_ids in chain_ids:
                if possible_chain_ids in file:
                    found_chain_id = True
            assert found_chain_id, f"should be one of {chain_ids} but {file}"

        def _make_sure_file_extension_is_xml(self, file_name):
            """make sure the file extension is xml"""
            file_ext = file_name.split(".")[-1]
            assert file_ext == "xml", f" should be xml but {file_ext}, file:{file_name}"

        def _make_sure_file_is_not_empty(self, full_file_path):
            """make sure the files is not empty"""
            assert os.path.getsize(full_file_path) != 0

        def _clean_scarpe_delete(
            self, init_scraper_function, dump_path="temp", limit=None, file_type=None
        ):

            self._delete_download_folder(dump_path)
            os.makedirs(dump_path)

            try:
                scraper = init_scraper_function(folder_name=dump_path)

                kwarg = {"limit": limit, "files_types": file_type}

                scraper.scrape(**kwarg)

                files_found = os.listdir(dump_path)
                assert len(files_found) == 1, "only one folder should exists"

                download_path = os.path.join(dump_path, files_found[0])
                files_found = os.listdir(download_path)

                if not scraper.is_validate_scraper_found_no_files(
                    limit=limit, files_types=file_type
                ):
                    self._make_sure_filter_work(
                        files_found, file_type=file_type, limit=limit
                    )

                for file in files_found:
                    self._make_sure_file_contain_chain_ids(scraper.get_chain_id(), file)
                    self._make_sure_file_extension_is_xml(file)
                    self._make_sure_file_is_not_empty(os.path.join(download_path, file))

            finally:
                self._delete_download_folder(dump_path)

        def _get_temp_folder(self):
            """get a temp folder to download the files into"""
            return self.folder_name + str(uuid.uuid4().hex)

        def test_scrape_one(self):
            """scrape one file and make sure it exists"""
            self._clean_scarpe_delete(
                init_scraper_function, self._get_temp_folder(), limit=1
            )

        def test_scrape_ten(self):
            """scrape ten file and make sure they exists"""
            self._clean_scarpe_delete(
                init_scraper_function, self._get_temp_folder(), limit=10
            )

        def test_scrape_promo(self):
            """scrape one promo file and make sure it exists"""
            self._clean_scarpe_delete(
                init_scraper_function,
                self._get_temp_folder(),
                limit=1,
                file_type=FileTypesFilters.only_promo(),
            )

        def test_scrape_store(self):
            """scrape one store file and make sure it exists"""
            self._clean_scarpe_delete(
                init_scraper_function,
                self._get_temp_folder(),
                limit=1,
                file_type=FileTypesFilters.only_store(),
            )

        def test_scrape_price(self):
            """scrape one price file and make sure it exists"""
            self._clean_scarpe_delete(
                init_scraper_function,
                self._get_temp_folder(),
                limit=1,
                file_type=FileTypesFilters.only_price(),
            )

        # def test_scrape_all_no_failures(self):
        #     with mock.patch("il_supermarket_scarper.utils.mongo.ScraperStatus.on_download_completed") as mongo:
        #         self._clean_scarpe_delete(scraperInit,self.get_temp_folder())

        #     for call in mongo.call_args_list:
        #         for arg in call[1]['results']:
        #             assert arg["downloaded"] or 'EMPTY_FILE' in arg['error'], f"{arg} should be downloaded"

    return TestScapers
