import json

import requests
from retry import retry
from urllib.request import urlretrieve

from .apsx import Aspx
from il_supermarket_scarper.utils import Logger,download_connection_retry,url_connection_retry
class Bina(Aspx):
    # possibly can support historical search: as a date search menu
    
    def __init__(self, chain, chain_id, url_perfix, download_postfix="/Download.aspx?FileNm=",domain="binaprojects.com/", folder_name=None):
        super().__init__(chain, chain_id, url=f"http://{url_perfix}.{domain}",  aspx_page="MainIO_Hok.aspx", folder_name=folder_name)
        self.download_postfix = download_postfix

    def get_data_from_page(self,req_res):
        return json.loads(req_res.text)

    def get_entry_href(self,x):
        return self.download_postfix+x['FileNm']

    def get_file_name_no_ext(self,x):
        return x.split(self.download_postfix)[-1].split(".")[0]

    @url_connection_retry()
    def session_and_check_status(self,url):
        Logger.info("On a new Session: calling {}".format(url))
        session = requests.Session()

        # get the download link
        response_content = session.get(url)
        
        if response_content.status_code != 200:
            Logger.info("Got status code: {}, body is {} ".format(response_content.status_code,response_content.text))

            raise ConnectionError(f"response for {url}, returned with status {response_content.status_code}")

        spath = json.loads(response_content.content)
        Logger.info("Found spath: {}".format(spath))
        
        return spath[0]['SPath']

    @download_connection_retry()
    def retrieve_file(self,file_link, file_save_path):
        url = self.session_and_check_status(file_link)

        ext = file_link.split(".")[-1]
        
        urlretrieve(url,file_save_path+"."+ext)
        return file_save_path+"."+ext
