from il_supermarket_scarper.engines import Shufersal as ShufersalEngine
import re

class YaynotBitan(ShufersalEngine):

    def __init__(self,folder_name=None):
        super().__init__(chain="YaynotBitan", chain_id="7290725900003", 
                            base_url="http://publishprice.ybitan.co.il/",
                            folder_name=folder_name)

    
    def get_total_pages(self, html):
        return int(re.findall(".*?page\=([0-9]*)$", html.xpath('//*[@class="page_link"]//a/@href')[-1])[0])


    def collect_file_links(self, html):
        links = []
        filenames = []
        for element in html.xpath('//*/tr')[1:]: # skip header
            links.append(self.base_url + element.xpath("./td[6]/a/@href")[0])
            filenames.append(element.xpath("./td[2]")[0].text)
        return links,filenames