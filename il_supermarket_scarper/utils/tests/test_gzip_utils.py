import os
import pytest
from io import BytesIO

from il_supermarket_scarper.utils.gzip_utils import extract_xml_file_from_gz


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
            
        buffer = BytesIO(file_content)

    with pytest.raises(ValueError):
        extract_xml_file_from_gz(buffer, file_name)

    if file_content is not None and not os.path.exists(file_path):
        with open(file_path, "wb") as f:
            f.write(file_content)
