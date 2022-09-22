import os,time
import requests
from retry import retry
from abc import ABC
import asyncio
import concurrent.futures
from urllib.request import urlretrieve 
from il_supermarket_scarper.utils import get_output_folder,FileTypesFilters,Logger,ScraperStatus,Gzip

class Engine(ScraperStatus,FileTypesFilters,ABC):

    def __init__(self,chain,chain_id,folder_name=None,):
        super().__init__(chain)
        self.chain = chain
        self.chain_id = chain_id
        if folder_name:
            self.storage_path = os.path.join(folder_name,self.chain)
        else:
            self.storage_path = get_output_folder(self.chain)
        Logger.info("Storage path: {}".format(self.storage_path))



    def get_storage_path(self):
        return self.storage_path
    
    def _validate_scraper_found_no_files(self):
        return True

    def _apply_limit(self,intreable,limit=None,files_types=None,by=None):
        intreable_ = self.filter_already_downloaded(self.storage_path,intreable,by=by)
        intreable_ = self.unique(intreable_,by=by)
        if files_types:
            intreable_ = list()
            for type_ in files_types:
                type_files = self.filter(type_,intreable,by=by)
                if limit:
                    type_files = type_files[:min(limit,len(type_files))]
                intreable_.extend(type_files)
        
        elif limit:
            assert limit > 0, "Limit must be greater than 0"
            Logger.info("Limit: {}".format(limit))
            intreable_ = intreable_[:min(limit,len(intreable_))]
        Logger.info("Result length {}".format(len(intreable_))) 

        if len(intreable_) == 0 and self._validate_scraper_found_no_files():
            raise ValueError("No files to download for file {}".format(files_types))
        return intreable_

    @classmethod
    def unique(cls, iterable,by=None):
        """Returns the type of the file."""
        seen = set()
        result = list()
        if not by:
            by = lambda x: x
        for item in iterable:
            k  = by(item)
            if k not in seen:
                seen.add(k)
                result.append(item)
                
        return result

    @retry(ConnectionError, delay=5, tries=6)
    def request_and_check_status(self,url):

        Logger.info("Requesting url: {}".format(url))
        req_res: requests.Response = requests.get(url)

        if req_res.status_code != 200:
            Logger.info("Got status code: {}, body is {} ".format(req_res.status_code,req_res.text))
            raise ConnectionError(f"response for {url}, returned with status {req_res.status_code}")

        return req_res

    def post(self):
        cookie_file = f"{self.chain}_cookies.txt"
        if os.path.exists(cookie_file):
            os.remove(cookie_file)
        
    @retry(ConnectionError, delay=5, tries=6)
    def session_with_cookies(self,url):

        from http.cookiejar import MozillaCookieJar
        import requests

        session = requests.Session()
        session.cookies = MozillaCookieJar(f"{self.chain}_cookies.txt")
        try:
            session.cookies.load()
        except FileNotFoundError:
            Logger.info("didn't find cookie file")

        Logger.info("On a new Session requesting url: {}".format(url))

        response_content = session.get(url)
        
        if response_content.status_code != 200:
            Logger.info("On Session, Got status code: {}, body is {} ".format(response_content.status_code,response_content.text))
            raise ConnectionError(f"response for {url}, returned with status {response_content.status_code}")

        if not os.path.exists(f"{self.chain}_cookies.txt"):
            session.cookies.save()
        return response_content

    def scrape(self,limit=None,files_types=None):
        self.on_scraping_start(limit=limit,files_types=files_types)
        Logger.info("Starting scraping for {}".format(self.chain))
        self.make_storage_path_dir()  

    def make_storage_path_dir(self) -> None:
        if os.path.exists(self.storage_path):
            return
        os.makedirs(self.storage_path)

    def get_chain_id(self):
        if type(self.chain_id) == list:
            return self.chain_id
        return [self.chain_id]
    
    def get_chain_name(self):
        return self.chain

    def defualt_aggregtion_function(all_done):
        result = [] 
        for response in all_done:
            result.append(response.result())
        return result

    def get_event_loop(self):
        try:
             return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def execute_in_event_loop(self,function_to_execute,iterable,aggregtion_function=defualt_aggregtion_function):
        loop = self.get_event_loop()
        return loop.run_until_complete(self.run_task_async(function_to_execute,iterable,aggregtion_function=aggregtion_function))

    async def run_task_async(self,function_to_execute,iterable,aggregtion_function=defualt_aggregtion_function):
        loop = self.get_event_loop()
        
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for arg in iterable:
                futures.append(loop.run_in_executor(
                    executor, 
                    function_to_execute, 
                    arg
                ))

        all_done,not_done = await asyncio.wait(futures)
        assert len(not_done) == 0, "Not all tasks are done, should be blocking."
        all_done = aggregtion_function(list(all_done))
        
        Logger.info("Done with {len} files".format(len=len(all_done)))
        return all_done
               
    def retrieve_file(self,file_link, file_save_path):
        file_save_path_res = file_save_path +"."+ file_link.split("?")[0].split(".")[-1]
        urlretrieve(file_link,file_save_path_res )
        return file_save_path_res

    def save_and_extract(self,arg):
        file_link,file_name = arg
        file_save_path = os.path.join(self.storage_path, file_name)
        Logger.info("Downloading {} to {}".format(file_link,file_save_path))
        downloaded,extract_succefully,error = self._save_and_extract(file_link,file_save_path)

        if error and ("Remote end closed connection without response" in error or "426 File transfer failed" in error):
            time.sleep(2)
            downloaded,extract_succefully,error = self._save_and_extract(file_link,file_save_path)
        
        return {
                "file_name":file_name,
                "downloaded":downloaded,
                "extract_succefully":extract_succefully,
                "error":error,
            }
            
    def _save_and_extract(self,file_link,file_save_path):
        downloaded = False
        extract_succefully = False
        error = None
        try:
            file_save_path_with_ext = self.retrieve_file(file_link, file_save_path)
            downloaded = True

            if file_save_path_with_ext.endswith("gz"):
                Gzip.extract_xml_file_from_gz_file(file_save_path_with_ext)

                os.remove(file_save_path_with_ext)
            extract_succefully = True

            Logger.info("Done downloading {}".format(file_link))
         
        except Exception as e:
            Logger.error("Error downloading {}".format(file_link))
            Logger.error(e)
            error = str(e)

        return downloaded,extract_succefully,error
        