import datetime
import re
import os
import enum
import holidays
import pytz
import lxml.html as lh
from bs4 import BeautifulSoup

from .logger import Logger
from .connection import session_with_cookies


def get_statue_page():
    """fetch the gov.il site"""
    url = "https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations"
    # Create a handle, page, to handle the contents of the website
    return session_with_cookies(url, chain_cookie_name="gov_il")


def get_status():
    """get the number of scarper listed on the gov.il site"""
    page = get_statue_page()
    # Store the contents of the website under doc
    doc = BeautifulSoup(page.content, features="lxml")
    # Parse data that are stored between <tr>..</tr> of HTML
    count = 0
    for element in doc.find_all("strong"):
        if "לצפייה במחירים" in str(element):
            count += 1

    return count


def get_status_date():
    """get the date change listed on the gov.il site"""
    page = get_statue_page()

    if page.status_code != 200:
        Logger.error(f"request as failed, page body is {page}.")
        raise ValueError("Failed reading the gov.il site.")
    line_with_date = (
        lh.fromstring(page.content)
        .xpath(
            r"""/html/body/section/div/
                                                        div[3]/div/span"""
        )[0]
        .text
    )
    Logger.info(f"line_with_date: {line_with_date}")

    dates = re.findall(
        r"([1-9]|1[0-9]|2[0-9]|3[0-1]|0[0-9])(.|-|\/)([1-9]|1[0-2]|0[0-9])(.|-|\/)(20[0-9][0-9])",
        line_with_date,
    )

    Logger.info(f"Found {len(dates)} dates")
    if len(dates) != 1:
        raise ValueError(f"found dates: {dates}")

    return datetime.datetime.strptime("".join(dates[0]), "%d.%m.%Y")


def get_output_folder(chain_name):
    """the the folder to write the chain fils in"""
    return os.path.join(_get_dump_folder(), chain_name)


def _get_dump_folder():
    """get the dump folder to locate the chains folders in"""
    return os.environ.get("XML_STORE_PATH", "dumps")


# Enum for size units
class UnitSize(enum.Enum):
    """enum represent the unit size in memory"""

    BYTES = "Bytes"
    KB = "Kb"
    MB = "Mb"
    GB = "Gb"


def convert_unit(size_in_bytes, unit):
    """Convert the size from bytes to other units like KB, MB or GB"""
    if unit == UnitSize.KB:
        return size_in_bytes / 1024
    if unit == UnitSize.MB:
        return size_in_bytes / (1024 * 1024)
    if unit == UnitSize.GB:
        return size_in_bytes / (1024 * 1024 * 1024)
    return size_in_bytes


def log_folder_details(folder, unit=UnitSize.MB):
    """log details about a folder"""
    unit_size = 0
    for path, dirs, files in os.walk(folder):
        # summerize all files
        Logger.info(f"Found the following files in {path}:")
        size = 0
        for file in files:
            if "xml" in file:
                full_file_path = os.path.join(path, file)
                fp_size = os.path.getsize(full_file_path)
                size += fp_size
                Logger.info(f"- file {full_file_path}: size {size}")

        unit_size = convert_unit(size, unit)
        Logger.info(f"Found the following folders in {path}:")
        for sub_folder in dirs:
            unit_size += log_folder_details(os.path.join(path, sub_folder), unit)

    Logger.info(f"Total size of {folder}: {unit_size} {unit.name}")

    return {"size": unit_size, "unit": unit.name}


def summerize_dump_folder_contant(dump_folder):
    """collect details about the dump folder"""

    Logger.info(" == Starting summerize dump folder == ")
    Logger.info(f"dump_folder = {dump_folder}")
    for any_file in os.listdir(dump_folder):
        current_file = os.path.join(dump_folder, any_file)
        if os.path.isdir(current_file):
            log_folder_details(current_file)
        else:
            Logger.info(f"- file {current_file}")


def clean_dump_folder(dump_folder):
    """clean the dump folder completly"""
    for any_file in os.listdir(dump_folder):
        current_file = os.path.join(dump_folder, any_file)
        if os.path.isdir(current_file):
            for file in os.listdir(current_file):
                full_file_path = os.path.join(current_file, file)
                os.remove(full_file_path)
            os.rmdir(current_file)
        else:
            os.remove(current_file)


def _now():
    return datetime.datetime.now(pytz.timezone("Asia/Jerusalem"))


def _is_saturday_in_israel():
    return _now().weekday() == 5


def _is_friday_in_israel():
    return _now().weekday() == 4


def _is_weekend_in_israel():
    return _is_friday_in_israel() or _is_saturday_in_israel()


def _is_holiday_in_israel():
    return _now().date() in holidays.IL()
