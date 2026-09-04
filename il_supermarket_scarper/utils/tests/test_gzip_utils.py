import gzip
import os
import zipfile
import io

import pytest

from il_supermarket_scarper.utils.gzip_utils import (
    extract_xml_from_gz_in_memory,
    is_compressed_content,
    validate_gzip_integrity,
    GZIP_MAGIC_BYTES,
    ZIP_MAGIC_BYTES,
    GZIP_OK,
    GZIP_TRUNCATED,
    GZIP_CRC_MISMATCH,
    GZIP_NOT_GZIP,
)

BAD_GZIP_FIXTURE = (
    "il_supermarket_scarper/utils/tests/PriceFull7290876100000-003-202410070010.gz"
)


def _good_gzip(payload=b"<xml>test content</xml>"):
    return gzip.compress(payload), payload


def test_unzip_bad_file():
    """Truncated on-disk fixture is classified as gzip truncated."""
    file_name = os.path.basename(BAD_GZIP_FIXTURE)
    with open(BAD_GZIP_FIXTURE, "rb") as handle:
        file_content = handle.read()

    integrity = validate_gzip_integrity(file_content)
    assert integrity.status == GZIP_TRUNCATED
    assert integrity.ok is False

    with pytest.raises(ValueError, match="gzip truncated"):
        extract_xml_from_gz_in_memory(file_content, file_name)


def test_extract_valid_gzip_uses_integrity_bytes():
    """Happy-path gzip extract returns the uncompressed payload."""
    compressed, payload = _good_gzip()
    assert extract_xml_from_gz_in_memory(compressed, "ok.gz") == payload


def test_extract_valid_zip_still_works():
    """Zip members are unchanged; integrity check is gzip-only."""
    payload = b"<xml>zipped</xml>"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("doc.xml", payload)
    assert extract_xml_from_gz_in_memory(buffer.getvalue(), "ok.zip") == payload


class TestValidateGzipIntegrity:
    """Classify complete, truncated, CRC-bad, and non-gzip payloads."""

    def test_ok_gzip(self):
        """Complete gzip member is ok and returns uncompressed bytes."""
        compressed, payload = _good_gzip()
        result = validate_gzip_integrity(compressed)
        assert result.status == GZIP_OK
        assert result.ok is True
        assert result.uncompressed == payload

    def test_truncated_gzip(self):
        """Dropping the gzip footer is truncated, not ok."""
        compressed, _payload = _good_gzip()
        result = validate_gzip_integrity(compressed[:-20])
        assert result.status == GZIP_TRUNCATED
        assert result.ok is False
        assert result.uncompressed is None

    def test_crc_mismatch(self):
        """Flipping the gzip CRC footer is crc_mismatch."""
        compressed, _payload = _good_gzip()
        mutated = bytearray(compressed)
        mutated[-8] ^= 0xFF
        result = validate_gzip_integrity(bytes(mutated))
        assert result.status == GZIP_CRC_MISMATCH
        assert "CRC" in result.detail or "crc" in result.detail.lower()

    def test_not_gzip_html(self):
        """HTML error pages are not_gzip."""
        result = validate_gzip_integrity(b"<html>link expired</html>")
        assert result.status == GZIP_NOT_GZIP

    def test_not_gzip_empty(self):
        """Empty buffers are not_gzip."""
        result = validate_gzip_integrity(b"")
        assert result.status == GZIP_NOT_GZIP
        assert "empty" in result.detail

    def test_not_gzip_plain_xml(self):
        """Uncompressed XML is not_gzip."""
        result = validate_gzip_integrity(b"<?xml version='1.0'?><root/>")
        assert result.status == GZIP_NOT_GZIP

    def test_extract_crc_mismatch_message(self):
        """Extract error text includes gzip crc_mismatch."""
        compressed, _payload = _good_gzip()
        mutated = bytearray(compressed)
        mutated[-8] ^= 0xFF
        with pytest.raises(ValueError, match="gzip crc_mismatch"):
            extract_xml_from_gz_in_memory(bytes(mutated), "bad.gz")


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
