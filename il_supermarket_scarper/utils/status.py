import datetime
import re
import os
import enum
import holidays
import pytz
from .logger import Logger
from .connection import get_from_latast_webpage, get_from_webpage


def get_statue_page(extraction_type, source="gov.il"):
    """fetch the gov.il site"""
    url = "https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations"
    # Create a handle, page, to handle the contents of the website

    if source == "gov.il":
        return get_from_latast_webpage(url, extraction_type=extraction_type)
    if source == "cache":
        return get_from_webpage(get_cached_page(), extraction_type=extraction_type)
    raise ValueError(f"source '{source}' is not valid.")


def get_cached_page():
    """get the current cached page"""
    cache = None
    with open(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "tests",
            "cpfta_prices_regulations",
        ),
        encoding="utf-8",
    ) as page_cache:
        cache = page_cache.read()
    return cache


def get_status():
    """get the number of scarper listed on the gov.il site"""
    links_text = get_statue_page(extraction_type="links_name")
    # Store the contents of the website under doc
    count = 0
    for element in links_text:
        if "לצפייה במחירים" in str(element) or "לצפיה במחירים" in str(element):
            count += 1

    return count


def get_status_date():
    """get the date change listed on the gov.il site"""
    line_with_date = get_statue_page(extraction_type="update_date")

    Logger.info(f"date in 'line_with_date' is '{line_with_date}'")

    dates = re.findall(
        r"([1-9]|1[0-9]|2[0-9]|3[0-1]|0[0-9])(.|-|\/)([1-9]|1[0-2]|0[0-9])(.|-|\/)(20[0-9][0-9])",
        line_with_date,
    )

    Logger.info(f"Found {len(dates)} dates")
    if len(dates) != 1:
        raise ValueError(f"found dates: {dates}")

    return datetime.datetime.strptime("".join(dates[0]), "%d.%m.%Y")


def get_output_folder(chain_name, folder_name=None):
    """the the folder to write the chain fils in"""
    return os.path.join(folder_name if folder_name else _get_dump_folder(), chain_name)


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


def convert_nl_size_to_bytes(size_str, to_unit=UnitSize.MB):
    """
    Parse human-readable file size string to bytes.
    Supports formats like: "10.5 MB", "1.2GB", "500 KB", "1234", etc.
    Returns bytes as integer, or None if parsing fails.
    """
    if not size_str:
        return None

    # Remove any extra whitespace and convert to uppercase
    size_str = size_str.strip().upper()

    # Pattern to match: number (with optional decimal) followed by optional unit
    pattern = r"([\d.]+)\s*(B|KB|MB|GB|TB)?"
    match = re.match(pattern, size_str)
    if not match:
        return None

    try:
        number = string_to_float(match.group(1))
        unit_str = match.group(2) if match.group(2) else "B"
        # Map string units to UnitSize enum where possible
        unit_map = {
            "B": UnitSize.BYTES,
            "KB": UnitSize.KB,
            "MB": UnitSize.MB,
            "GB": UnitSize.GB,
            # You can add "TB": UnitSize.TB if desired and defined
        }
        from_unit = unit_map.get(unit_str, UnitSize.BYTES)
        size_in_from_unit = number
        # convert_unit expects size in bytes, so we need to first get bytes from the given unit
        return convert_unit(size_in_from_unit, from_unit=from_unit, to_unit=to_unit)
    except (ValueError, TypeError, KeyError):
        return None


def string_to_float(size_str):
    """convert a string to a float"""
    return float(size_str.replace(",", ""))


def convert_unit(size_in_bytes, from_unit=UnitSize.BYTES, to_unit=UnitSize.MB):
    """Convert the size from bytes to other units like KB, MB or GB"""
    if from_unit == to_unit:
        return size_in_bytes
    # Convert size_in_bytes (in from_unit) to bytes
    if from_unit == UnitSize.KB:
        bytes_val = size_in_bytes * 1024
    elif from_unit == UnitSize.MB:
        bytes_val = size_in_bytes * 1024 * 1024
    elif from_unit == UnitSize.GB:
        bytes_val = size_in_bytes * 1024 * 1024 * 1024
    else:  # from_unit == UnitSize.BYTES
        bytes_val = size_in_bytes

    # Convert bytes to to_unit
    if to_unit == UnitSize.BYTES:
        return bytes_val
    if to_unit == UnitSize.KB:
        return bytes_val / 1024
    if to_unit == UnitSize.MB:
        return bytes_val / (1024 * 1024)
    if to_unit == UnitSize.GB:
        return bytes_val / (1024 * 1024 * 1024)
    return bytes_val


def log_folder_details(folder, unit=UnitSize.MB):
    """log details about a folder"""
    size = 0
    files_scaned = []
    Logger.info(f"Found the following files in {folder}")

    for path, _, files in os.walk(folder):

        # summerize all files
        for file in files:
            if "xml" in file:
                full_file_path = os.path.join(path, file)
                size += os.path.getsize(full_file_path)
                files_scaned.append(full_file_path)
                Logger.info(f"- file {full_file_path}: size {size}")

        # unit_size =
        # for sub_folder in dirs:
        #     unit_size += log_folder_details(os.path.join(path, sub_folder), unit)

    Logger.info(
        f"Folder {folder}: Num of Files= {len(files_scaned)},"
        f"Size= {convert_unit(size, unit)} {unit.name}"
    )

    return {
        "size": convert_unit(size, from_unit=UnitSize.BYTES, to_unit=unit),
        "unit": unit.name,
        "folder": folder,
        "folder_content": files_scaned,
    }


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


def hour_files_expected_to_be_accassible():
    """the hour (AM) in which the files are expected to be published in IL time"""
    return 12


def _now():
    return datetime.datetime.now(pytz.timezone("Asia/Jerusalem"))


def _testing_now(hour_consider_stable=hour_files_expected_to_be_accassible()):
    current_time = _now()

    if current_time.hour < hour_consider_stable:
        current_time = current_time - datetime.timedelta(hours=hour_consider_stable)
    return current_time


def datetime_in_tlv(year, month, day, hour, minute, second):
    """return a datedatiem in tlv timezone"""
    return datetime.datetime(
        year, month, day, hour, minute, second, tzinfo=pytz.timezone("Asia/Jerusalem")
    )


def _is_saturday_in_israel(date=None):
    if not date:
        date = _now()
    return date.weekday() == 5


def _is_friday_in_israel():
    return _now().weekday() == 4


def _is_weekend_in_israel():
    return _is_friday_in_israel() or _is_saturday_in_israel()


def _is_holiday_in_israel():
    return _now().date() in holidays.CountryHoliday("IL")
