import os
import pytest

from il_supermarket_scarper.utils.gzip_utils import extract_xml_from_gz_in_memory


def test_unzip_bad_file():
    """test unziping a bad file"""

    file_path = (
        "il_supermarket_scarper/utils/tests/PriceFull7290876100000-003-202410070010.gz"
    )
    file_name = "PriceFull7290876100000-003-202410070010.gz"
    file_content = None
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            file_content = f.read()

    with pytest.raises(ValueError):
        extract_xml_from_gz_in_memory(file_content, file_name)
