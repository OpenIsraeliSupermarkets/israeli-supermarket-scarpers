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
        folder_name=None,
    ):
        super().__init__(chain, chain_id, url, aspx_page, folder_name=folder_name)
        self.chain_hebrew_name = chain_hebrew_name

    # def get_file_types_id(self, files_types=None):
    #     """get the file type id"""
    #     if files_types is None:
    #         return "all"

    #     types = []
    #     for ftype in files_types:
    #         if ftype == FileTypesFilters.STORE_FILE.name:
    #             types.append("storefull")
    #         if ftype == FileTypesFilters.PRICE_FILE.name:
    #             types.append("price")
    #         if ftype == FileTypesFilters.PROMO_FILE.name:
    #             types.append("promo")
    #         if ftype == FileTypesFilters.PRICE_FULL_FILE.name:
    #             types.append("pricefull")
    #         if ftype == FileTypesFilters.PROMO_FULL_FILE.name:
    #             types.append("promofull")
    #     return types

    # def get_when(self, when_date):
    #     """get the when date"""
    #     if when_date is None:
    #         when_date = _now()
    #     return when_date.strftime("%d/%m/%Y")

    # def get_chain_n_stores__id(self, store_id=None, c_id=None):
    #     """get the store id"""
    #     if store_id is None:
    #         chain_id = str(c_id)  # + "001"
    #         store_id = "-1"
    #     else:
    #         chain_id = str(c_id)
    #         store_id = str(c_id) + "001" + str(store_id).zfill(3)
    #     return chain_id, store_id

    def _build_query_url(self, query_params, base_urls):
        res = []
        for base in base_urls:
            res.append(
                {
                    "method": "GET",
                    "url": base,
                    # "body": query_params,
                }
            )
        return res

    def _get_all_possible_query_string_params(
        self, files_types=None, store_id=None, when_date=None
    ):
        """get the arguments need to add to the url"""

        return [{}]
        # post_body = []
        # if isinstance(self.chain_id, list):
        #     for c_id in self.chain_id:
        #         chain_id, store_id = self.get_chain_n_stores__id(
        #             store_id=store_id, c_id=c_id
        #         )
        #         post_body.append(
        #             {

        #                 "ctl00$TextArea": "",
        #                 "ctl00$MainContent$chain": chain_id,
        #                 "ctl00$MainContent$subChain": "-1",
        #                 "ctl00$MainContent$branch": store_id,
        #                 "ctl00$MainContent$txtDate": self.get_when(when_date=when_date),
        #                 "ctl00$MainContent$fileType": "all",
        #                 # "ctl00$MainContent$btnSearch": "חיפוש",
        #             }
        #         )
        # else:
        #     chain_id, store_id = self.get_chain_n_stores__id(
        #         store_id=store_id, c_id=self.chain_id
        #     )
        #     post_body.append(
        #         {
        #             "ctl00$TextArea": "",
        #             "ctl00$MainContent$chain": chain_id,
        #             "ctl00$MainContent$subChain": "-1",
        #             "ctl00$MainContent$branch": store_id,
        #             "ctl00$MainContent$txtDate": self.get_when(when_date=when_date),
        #             "ctl00$MainContent$fileType": "all",
        #             "ctl00$MainContent$btnSearch": "חיפוש",
        #         }
        #     )

        # # add file types to url
        # if files_types:
        #     chains_urls_with_types = []
        #     for files_type in self.get_file_types_id(files_types=files_types):
        #         for chain_url in post_body:
        #             chain_url["ctl00$MainContent$fileType"] = files_type
        #             chains_urls_with_types.append(chain_url)
        #     post_body = chains_urls_with_types

        # return post_body

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
