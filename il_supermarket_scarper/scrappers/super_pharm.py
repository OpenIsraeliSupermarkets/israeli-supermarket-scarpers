from il_supermarket_scarper.engines import MultiPageWeb
from il_supermarket_scarper.utils import Logger
import re,json
from pathlib import Path
class SuperPharm(MultiPageWeb):

    def __init__(self,folder_name=None):
        super().__init__(chain="Super-Pharm", chain_id="7290172900007", 
                            url="http://prices.super-pharm.co.il/",
                            folder_name=folder_name)

    
    def get_total_pages(self, html):
        return int(re.findall(".*?page\=([0-9]*)$", html.xpath('//*[@class="page_link"]//a/@href')[-1])[0])

    def collect_file_links(self, html):
        links = []
        filenames = []
        for element in html.xpath('//*/tr')[1:]: # skip header
            links.append(self.url + element.xpath("./td[6]/a/@href")[0])
            filenames.append(element.xpath("./td[2]")[0].text.split(".")[0])
        return links,filenames


    def retrieve_file(self,file_link, file_save_path):
        Logger.info("On a new Session: calling {}".format(file_link))

        response_content = self.session_with_cookies(file_link)
        spath = json.loads(response_content.content)

        Logger.info("Found spath: {}".format(spath))

        file_to_save = self.session_with_cookies(self.url + spath['href'])

        file_with_ext = file_save_path + ".gz"


        Path(file_with_ext).write_bytes(file_to_save.content)
        return file_with_ext