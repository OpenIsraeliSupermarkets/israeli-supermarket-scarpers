import gzip
import shutil
import os
import io
import zipfile
from .exceptions import RestartSessionError


def extract_xml_file_from_gz_file(file_save_path):
    """extract xml from gz"""
    try:
        with gzip.open(file_save_path, "rb") as infile:
            with open(os.path.splitext(file_save_path)[0] + ".xml", "wb") as outfile:
                shutil.copyfileobj(infile, outfile)
    except gzip.BadGzipFile:
        try:
            with open(file_save_path, "rb") as response_content:
                with zipfile.ZipFile(io.BytesIO(response_content.read())) as the_zip:
                    zip_info = the_zip.infolist()[0]
                    with the_zip.open(zip_info) as the_file:
                        with open(
                            os.path.splitext(file_save_path)[0] + ".xml", "wb"
                        ) as f_out:
                            f_out.write(the_file.read())

        except Exception as exception:  # pylint: disable=broad-except
            report_failed_zip(exception, file_save_path)

    except Exception as exception:  # pylint: disable=broad-except
        report_failed_zip(exception, file_save_path)


def report_failed_zip(exception, file_save_path):
    """report a file wasn't able to extracted"""
    file_contant = ""
    with open(file_save_path, "r", encoding="utf-8") as file:
        file_contant = file.readlines()
    file_size = os.path.getsize(file_save_path)
    os.remove(file_save_path)

    if "link expired" in str(file_contant):
        raise RestartSessionError()

    raise ValueError(
        f"Error decoding file:{ file_save_path } with "
        f"error: {str(exception)} file size {str(file_size) } ,"
        f"file_contant {str(file_contant)}"
    )
