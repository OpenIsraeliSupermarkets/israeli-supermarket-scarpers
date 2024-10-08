from il_supermarket_scarper.utils.gzip_utils import extract_xml_file_from_gz_file
import  pytest

def test_unzip_bad_file():
    """test unziping a bad file"""
    with pytest.raises(ValueError):
        extract_xml_file_from_gz_file("il_supermarket_scarper/utils/tests/PriceFull7290876100000-003-202410070010.gz")