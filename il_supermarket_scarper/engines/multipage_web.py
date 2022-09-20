import re
import lxml.html
import ntpath

from urllib.parse import urlsplit
from .web import WebBase
from il_supermarket_scarper.utils import Logger


class MultiPageWeb(WebBase):
    # seems like can't support histrical data.
    
    target_file_extension = '.xml'
    results_in_page = 20

    def __init__(self, chain, chain_id,url='http://prices.shufersal.co.il/', folder_name=None):
        super().__init__(chain, chain_id,url=url, folder_name=folder_name)

    def get_total_pages(self, html):
        return int(re.findall("^\/\?page\=([0-9]{2})$", html.xpath('//*[@id="gridContainer"]/table/tfoot/tr/td/a[6]/@href')[0])[0])

    def collect_details_from_site(self,limit=None,files_types=None):
        self.post()
        url = self.get_request_url()
        assert len(url) == 1, "should be only one url"
        url = url[0]

        html = lxml.html.parse(url)
        #    possible need:     html = lxml.html.fromstring(self.session_with_cookies(url).text)

        
        total_pages = self.get_total_pages(html)
        Logger.info("Found {} pages".format(total_pages))

        pages_to_scrape = list(map(lambda page_number: self.url + '?page=' + str(page_number),range(1, total_pages + 1)))
        #pages_to_scrape = self._apply_limit(pages_to_scrape,limit=limit,files_types=files_types)
        
        def multiple_page_aggregtion(pages_to_scrape):
            download_urls = list()
            file_names = list()
            for result in pages_to_scrape:
                page_download_urls,page_file_names = result.result()
                download_urls.extend(page_download_urls)
                file_names.extend(page_file_names)
            return download_urls,file_names

        download_urls,file_names = self.execute_in_event_loop(self.collect_links,pages_to_scrape,aggregtion_function=multiple_page_aggregtion)

        #download_urls = self._apply_limit(,limit=limit,files_types=files_types)
        file_names,download_urls = list(zip(*self._apply_limit(list(zip(file_names,download_urls)),limit=limit,files_types=files_types,by=lambda x:x[0])))

        return download_urls,file_names

    def collect_file_links(self, html):
        links = []
        filenames = []
        for link in html.xpath('//*[@id="gridContainer"]/table/tbody/tr/td[1]/a/@href'):
            links.append(link)
            filenames.append(ntpath.basename(urlsplit(link).path).split(".")[0])
        return links,filenames

    def collect_links(self,page,limit=None,files_types=None):

        response = self.session_with_cookies(page)
        
        html = lxml.html.fromstring(response.text)

        file_links,filenames = self.collect_file_links(html)
        Logger.info("Page {}: Found {} files".format(page,len(file_links)))

        filenames,file_links = list(zip(*self._apply_limit(list(zip(filenames,file_links)),limit=limit,files_types=files_types,by=lambda x:x[0])))
        Logger.info("After applying limit: Page {}: Found {} line and {} files".format(page,len(file_links),len(filenames)))
        
        return file_links,filenames
            
