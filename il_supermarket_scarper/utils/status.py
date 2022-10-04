import requests
import lxml.html as lh
from bs4 import BeautifulSoup
import re
import os
import datetime 
import pytz

    
from .logger import Logger

def get_status():
    url = "https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations"
    #Create a handle, page, to handle the contents of the website
    page = requests.get(url)
    #Store the contents of the website under doc
    doc = BeautifulSoup(page.content, features='lxml')
    #Parse data that are stored between <tr>..</tr> of HTML
    count = 0
    for element in doc.find_all('strong'):
        if "לצפייה במחירים" in str(element):
            count +=1

    return count


def get_status_date():
    url = "https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations"
    #Create a handle, page, to handle the contents of the website\
    page = requests.get(url)

    if page.status_code != 200:
        Logger.error(f"request as failed, page body is {page}.")
        raise ValueError(f"Failed reading site {url}.")
    line_with_date = lh.fromstring(page.content).xpath('/html/body/section/div/div[3]/div/span')[0].text
    Logger.info("line_with_date: {}".format(line_with_date))
    
    dates = re.findall('([1-9]|1[0-9]|2[0-9]|3[0-1]|0[0-9])(.|-|\/)([1-9]|1[0-2]|0[0-9])(.|-|\/)(20[0-9][0-9])',line_with_date)

    Logger.info("Found {} dates".format(len(dates)))
    if len(dates) != 1:
        raise ValueError(f"found dates: {dates}")

    return datetime.datetime.strptime("".join(dates[0]),"%d.%m.%Y")


def get_all_listed_scarpers():
    from il_supermarket_scarper.engines.engine import Engine
    import il_supermarket_scarper.scrappers as scrappers
    all_scrapers = list()
    for _,value in scrappers.__dict__.items():
        if callable(value) and isinstance(value(),Engine):
            all_scrapers.append(value)
    return all_scrapers

def get_all_listed_scarpers_class_names():
    result = list()
    for class_instance in get_all_listed_scarpers():
        result.append( class_instance.__name__)
    return result

def get_scraper_by_class(class_names):
    for class_instance in get_all_listed_scarpers():  
        if class_instance.__name__ == class_names:
            return class_instance
    raise ValueError("class_names {} not found".format(class_names))

def get_output_folder(chain_name):
    return os.path.join(_get_dump_folder(), chain_name)
    
def _get_dump_folder():
    return os.environ.get('XML_STORE_PATH',"dumps")

import enum
# Enum for size units
class SIZE_UNIT(enum.Enum):
   BYTES = "Bytes"
   KB = "Kb"
   MB = "Mb"
   GB = "Gb"
def convert_unit(size_in_bytes, unit):
   """ Convert the size from bytes to other units like KB, MB or GB"""
   if unit == SIZE_UNIT.KB: 
       return size_in_bytes/1024  
   elif unit == SIZE_UNIT.MB:
       return size_in_bytes/(1024*1024)
   elif unit == SIZE_UNIT.GB:
       return size_in_bytes/(1024*1024*1024)
   else:
       return size_in_bytes

def log_folder_details(folder,unit=SIZE_UNIT.MB):
    from .logger import Logger
    unit_size = 0
    for path, dirs, files in os.walk(folder):
        # summerize all files
        Logger.info("Found the following files in {}:".format(path))
        size = 0
        for f in files:
            if "xml" in f:
                fp = os.path.join(path, f)
                fp_size = os.path.getsize(fp)
                size += fp_size
                Logger.info("- file {}: size {}".format(fp, size))
        
        unit_size = convert_unit(size,unit)
        Logger.info("Found the following folders in {}:".format(path))
        for folder in dirs:
            unit_size += log_folder_details(os.path.join(path, folder),unit)

    Logger.info("Total size of {}: {} {}".format(path, unit_size, unit.name))
    
    return {"size":unit_size,
            "unit":unit.name}

def summerize_dump_folder_contant(dump_folder):
    from .logger import Logger
    import os

    Logger.info(" == Starting summerize dump folder == ")
    Logger.info("dump_folder = {}".format(dump_folder))
    for any_file in os.listdir(dump_folder):
        current_file = os.path.join(dump_folder,any_file)
        if os.path.isdir(current_file):
            log_folder_details(current_file)
        else:
            Logger.info("- file {}".format(current_file))


def clean_dump_folder(dump_folder):
    from .logger import Logger
    import os

    for any_file in os.listdir(dump_folder):
        current_file = os.path.join(dump_folder,any_file)
        if os.path.isdir(current_file):
            for f in os.listdir(current_file):
                fp = os.path.join(current_file, f)
                os.remove(fp)
            os.rmdir(current_file)
        else:
            os.remove(current_file)

def _is_saturday_in_israel():
    return datetime.datetime.now(pytz.timezone("Asia/Jerusalem")).weekday() == 5
