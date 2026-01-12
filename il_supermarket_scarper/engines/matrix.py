from bs4 import BeautifulSoup
from il_supermarket_scarper.utils import Logger
from .apsx import Aspx


class Matrix(Aspx):
    """scraper for all matrix base site.
    (support adveanced search: follow the instrucation the page)"""

    utilize_date_param = False

    def __init__(
        self,
        chain,
        chain_id,
        url="https://laibcatalog.co.il/",
        aspx_page="NBCompetitionRegulations.aspx",
        chain_hebrew_name=None,
        file_output=None,
        status_database=None,
    ):
        super().__init__(chain, chain_id, url, aspx_page, file_output=file_output, status_database=status_database)
        self.chain_hebrew_name = chain_hebrew_name

    async def _build_query_url(self, query_params, base_urls):
        for base in base_urls:
            yield {
                "method": "GET",
                "url": base,
                # "body": query_params,
            }

    async def _get_all_possible_query_string_params(
        self, files_types=None, store_id=None, when_date=None
    ):
        """get the arguments need to add to the url"""

        yield {}

    def get_href_from_entry(self, entry):
        """get download link for entry (tr)"""
        return entry.a.attrs["href"]

    def get_file_name_no_ext_from_entry(self, entry):
        """get the file name without extensions from entey (tr)"""
        return entry.split("/")[-1].split(".gz")[0].split(".")[0]

    def get_data_from_page(self, req_res):
        soup = BeautifulSoup(req_res.text, features="lxml")
        all_trs = list(soup.find_all("tr"))[1:]  # skip title

        Logger.info(f"Before filtring names found {len(all_trs)} entries")
        if self.chain_hebrew_name:
            all_trs = list(
                filter(lambda x: x and self.chain_hebrew_name in str(x), all_trs)
            )
            Logger.info(f"After filtering names found {len(all_trs)} entries")
        return all_trs
