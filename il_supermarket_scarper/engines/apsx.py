from abc import ABC, abstractmethod
from il_supermarket_scarper.utils import Logger

from .web import WebBase

class Aspx(WebBase,ABC):

    def __init__(self, chain, chain_id,url,aspx_page,folder_name=None):
        super().__init__(chain, chain_id,url, folder_name=folder_name)
        self.aspx_page = aspx_page
    
    def get_aditional_url(self):
        if type(self.chain_id) is list:
            res = list()
            for c_id in self.chain_id:
                res.append(f"?code=={c_id}")
            return res
        return [f"?code={self.chain_id}"]

    def extract_task_from_entry(self,all_trs):
        download_urls: list = list(map(lambda x: self.url + self.get_entry_href(x),all_trs))
        file_names: list = list(map(lambda x: self.get_file_name_no_ext(x) ,download_urls))
        return download_urls,file_names

    def _build_url(self,aditional_url):
        res = list()
        for base in super().get_request_url():
            res.append(base + self.aspx_page + aditional_url)
        return res

    def get_request_url(self):
        result = list()
        for aditional_url in self.get_aditional_url():
            result.extend(self._build_url(aditional_url))
        Logger.info(f"Request url: {result}")
        return result

    @abstractmethod
    def get_entry_href(self,x):
        pass

    @abstractmethod
    def get_file_name_no_ext(self,x):
        pass