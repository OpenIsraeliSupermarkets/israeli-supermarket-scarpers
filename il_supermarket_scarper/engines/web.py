from bs4 import BeautifulSoup
from .engine import Engine
from il_supermarket_scarper.utils import Logger,execute_in_event_loop


class WebBase(Engine):
    """ scrape the file of websites that the only why to download them is via web """
    def __init__(self, chain, chain_id,url, folder_name=None):
        super().__init__(chain, chain_id, folder_name)
        self.url = url

    def get_data_from_page(self,req_res):
        """ get the file list from a page """
        soup = BeautifulSoup(req_res.text, features='lxml')
        return soup.find_all('tr')[1:]

    def get_request_url(self):
        """ get all links to collect download links from """
        return [self.url]

    def extract_task_from_entry(self,all_trs):
        """ extract download links and file names from page list """
        download_urls: list = list(map(lambda x: self.url + x.a.attrs['href'],all_trs))
        file_names: list = list(map(lambda x: x.a.attrs['href'].split(".")[0]
                                                                .split("/")[-1],all_trs))

        return download_urls,file_names

    def collect_files_details_from_site(self,limit=None, files_types=None):
        """ collect all enteris to download from site """
        urls_to_collect_link_from = self.get_request_url()

        all_trs = list()
        for url in urls_to_collect_link_from:
            req_res = self.request_and_check_status(url)
            trs = self.get_data_from_page(req_res)
            all_trs.extend(trs)

        Logger.info(f"Found {len(all_trs)} entries")

        download_urls,file_names = self.extract_task_from_entry(all_trs)

        if len(download_urls) > 0:
            file_names,download_urls = list(zip(*self._apply_limit(list(zip(file_names,
                                                                            download_urls)),
                                                    limit=limit,files_types=files_types,
                                                    by=lambda x:x[0])))

            Logger.info(f"After applying limit: Found {len(all_trs)} entries")

        return download_urls,file_names

    def scrape(self, limit=None,files_types=None):
        """ scarpe the files from multipage sites """
        super().scrape(limit,files_types=files_types)

        download_urls,file_names = self.collect_files_details_from_site(limit=limit,
                                                                  files_types=files_types)
        self.on_collected_details(url_to_download=download_urls,file_names_to_store=file_names)

        Logger.info(f"collected {len(download_urls)} to download.")
        if len(download_urls) > 0:
            results = execute_in_event_loop(self.save_and_extract,
                                            zip(download_urls, file_names),
                                            max_workers=self.max_workers)
        else:
            results = {}
        self.on_download_completed(results=results)
        self.on_scrape_completed(self.get_storage_path())
        self.post_scraping()
