import os
import pytest

from il_supermarket_scarper.utils.gzip_utils import extract_xml_file_from_gz_file


def test_unzip_bad_file():
    """test unziping a bad file"""

    file_path = (
        "il_supermarket_scarper/utils/tests/PriceFull7290876100000-003-202410070010.gz"
    )
    file_content = None
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            file_content = f.read()

    with pytest.raises(ValueError):
        extract_xml_file_from_gz_file(file_path)

    if file_content is not None and not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(file_content)
