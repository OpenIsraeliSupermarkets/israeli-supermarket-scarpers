

from bs4 import BeautifulSoup

from .apsx import Aspx
from il_supermarket_scarper.utils import Logger

class Matrix(Aspx):
    # support adveanced search: follow the instrucation the page >> להוראות עבור חיפוש מתקדם לחץ כאן

    def __init__(self, chain, chain_id, chain_hebrew_name=None, url="http://matrixcatalog.co.il/",aspx_page="NBCompetitionRegulations.aspx",folder_name=None):
        super().__init__(chain, chain_id,url,aspx_page,folder_name=folder_name)
        self.chain_hebrew_name = chain_hebrew_name

    
    def get_entry_href(self,x):
        return x.a.attrs['href']

    def get_file_name_no_ext(self,x):
        return x.split("/")[-1].split(".gz")[0].split(".")[0]

    def get_data_from_page(self,req_res):
        soup = BeautifulSoup(req_res.text, features='lxml')
        all_trs = list(soup.find_all('tr'))[1:] # skip title

        Logger.info("Found {} entries".format(len(all_trs)))
        if self.chain_hebrew_name:
            all_trs = list(filter(lambda x:x and self.chain_hebrew_name in str(x),all_trs))
            Logger.info("After filtering with {}: Found {} entries".format(self.chain_hebrew_name,len(all_trs)))
        return all_trs