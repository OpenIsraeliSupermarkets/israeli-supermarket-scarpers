from bs4 import BeautifulSoup

from il_supermarket_scarper.utils import Logger
from .apsx import Aspx


class Matrix(Aspx):
    """scraper for all matrix base site.
    (support adveanced search: follow the instrucation the page)"""

    def __init__(
        self,
        chain,
        chain_id,
        chain_hebrew_name=None,
        url="https://laibcatalog.co.il/",
        aspx_page="NBCompetitionRegulations.aspx",
        folder_name=None,
    ):
        super().__init__(chain, chain_id, url, aspx_page, folder_name=folder_name)
        self.chain_hebrew_name = chain_hebrew_name

    def get_href_from_entry(self, entry):
        """get download link for entry (tr)"""
        return entry.a.attrs["href"]

    def get_file_name_no_ext_from_entry(self, entry):
        """get the file name without extensions from entey (tr)"""
        return entry.split("/")[-1].split(".gz")[0].split(".")[0]

    def get_data_from_page(self, req_res):
        soup = BeautifulSoup(req_res.text, features="lxml")
        all_trs = list(soup.find_all("tr"))[1:]  # skip title

        Logger.info(f"Found {len(all_trs)} entries")
        if self.chain_hebrew_name:
            _all_trs = []
            for tr in all_trs:
                if tr and self.chain_hebrew_name in str(tr):
                    _all_trs.append(tr)
                else:
                    Logger.debug(f"Filtered out {str(tr)}")

            all_trs = _all_trs

            Logger.info(
                f"After filtering with {self.chain_hebrew_name}:"
                f"Found {len(all_trs)} entries"
            )
        return all_trs
