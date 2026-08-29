import gzip
import os
import pytest

from il_supermarket_scarper.utils.gzip_utils import (
    extract_xml_from_gz_in_memory,
    is_compressed_content,
    GZIP_MAGIC_BYTES,
    ZIP_MAGIC_BYTES,
)


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


class TestIsCompressedContent:
    """Tests for the is_compressed_content utility function."""

    def test_detects_gzip_content(self):
        """Test that gzip-compressed content is detected."""
        xml_content = b"<xml>test content</xml>"
        gzip_content = gzip.compress(xml_content)

        assert is_compressed_content(gzip_content) is True

    def test_detects_zip_magic_bytes(self):
        """Test that zip magic bytes (PK) are detected."""
        zip_content = ZIP_MAGIC_BYTES + b"rest of zip file content"

        assert is_compressed_content(zip_content) is True

    def test_detects_uncompressed_xml(self):
        """Test that plain XML content is not detected as compressed."""
        xml_content = b"<xml>test content</xml>"

        assert is_compressed_content(xml_content) is False

    def test_detects_uncompressed_text(self):
        """Test that plain text is not detected as compressed."""
        text_content = b"This is plain text content"

        assert is_compressed_content(text_content) is False

    def test_handles_empty_content(self):
        """Test that empty content returns False."""
        assert is_compressed_content(b"") is False

    def test_handles_single_byte(self):
        """Test that single byte content returns False."""
        assert is_compressed_content(b"\x1f") is False

    def test_exact_gzip_magic_bytes(self):
        """Test detection with exact gzip magic bytes."""
        content = GZIP_MAGIC_BYTES + b"rest of content"
        assert is_compressed_content(content) is True

    def test_exact_zip_magic_bytes(self):
        """Test detection with exact zip magic bytes."""
        content = ZIP_MAGIC_BYTES + b"rest of content"
        assert is_compressed_content(content) is True
