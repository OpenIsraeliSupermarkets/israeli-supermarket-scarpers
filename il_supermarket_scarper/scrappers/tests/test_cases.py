import unittest
import os,uuid
from il_supermarket_scarper.utils import FileTypesFilters
import mock

def make_test_case(scraperInit):

    class TestScapers(unittest.TestCase):

        def __init__(self,name) -> None:
            super().__init__(name)
            self.scraperInit = scraperInit
            self.folder_name = "temp"


        def _clean_scarpe_delete(cls,scraperInit,download_path="temp",limit=None,file_type=None):

            if os.path.isdir(download_path):
                cls._delete(download_path)
                os.removedirs(download_path)
            os.makedirs(download_path)
            assert len(os.listdir(download_path)) == 0
            
            try:
                scraper = scraperInit(folder_name=download_path)

                kwarg ={
                    "limit":limit,
                    "files_types":None
                }
                if file_type:
                    kwarg["files_types"]= file_type
                folder = scraper.get_storage_path()
                scraper.scrape(**kwarg)

                
                files_found = os.listdir(folder)
                if file_type:
                    filtered_files = 0
                    for f_type in file_type:
                        filtered_files+= len(FileTypesFilters.filter(f_type,files_found))
                    assert len(files_found) == filtered_files
                for file in files_found:
                    found_chain_id = False
                    file_ext = file.split(".")[-1]
                    chain_ids = scraper.get_chain_id()
                    for possible_chain_ids in chain_ids:
                        if possible_chain_ids in file:
                            found_chain_id = True
                    assert found_chain_id , f"should be one of {chain_ids} but {file}"
                    assert file_ext == "xml", f" should be xml but {file_ext}, file:{file}"
                    if os.path.getsize(os.path.join(folder,file)) == 0:
                        print()
                assert not limit or len(files_found) == limit," Found {files_found} files but should be {limit}"
            finally:
                for file in os.listdir(folder):
                    os.remove(os.path.join(folder,file))
                os.removedirs(folder)

        def _delete(cls,download_path):
            files_found = os.listdir(download_path)
            for file in files_found:
                file_path = os.path.join(download_path,file)
                if os.path.isdir(file_path):
                    os.rmdir(file_path)
                else:
                    os.remove(file_path)

        def get_temp_folder(self):
            return self.folder_name+str(uuid.uuid4().hex)

        def test_scrape_one(self):
            self._clean_scarpe_delete(scraperInit,self.get_temp_folder(),limit=1)

        def test_scrape_ten(self):
            self._clean_scarpe_delete(scraperInit,self.get_temp_folder(),limit=10)

        def test_scrape_promo(self):
            self._clean_scarpe_delete(scraperInit,self.get_temp_folder(),limit=1,file_type=FileTypesFilters.only_promo())

        def test_scrape_store(self):
            self._clean_scarpe_delete(scraperInit,self.get_temp_folder(),limit=1,file_type=FileTypesFilters.only_store())

        def test_scrape_price(self):
            self._clean_scarpe_delete(scraperInit,self.get_temp_folder(),limit=1,file_type=FileTypesFilters.only_price())

        # def test_scrape_all_no_failures(self):
        #     with mock.patch("il_supermarket_scarper.utils.mongo.ScraperStatus.on_download_completed") as mongo:
        #         self._clean_scarpe_delete(scraperInit,self.get_temp_folder())

        #     for call in mongo.call_args_list:
        #         for arg in call[1]['results']:
        #             assert arg["downloaded"] or 'EMPTY_FILE' in arg['error'], f"{arg} should be downloaded"
    
    return TestScapers