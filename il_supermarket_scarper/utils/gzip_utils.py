import gzip
import io
import shutil
import zipfile
from dataclasses import dataclass
from typing import Optional

from .exceptions import RestartSessionError

GZIP_MAGIC_BYTES = b"\x1f\x8b"
ZIP_MAGIC_BYTES = b"PK"

GZIP_OK = "ok"
GZIP_TRUNCATED = "truncated"
GZIP_CRC_MISMATCH = "crc_mismatch"
GZIP_NOT_GZIP = "not_gzip"


@dataclass(frozen=True)
class GzipIntegrity:
    """gzip member completeness + footer check.

    ``status`` is one of: ok, truncated, crc_mismatch, not_gzip.
    ``uncompressed`` is set only when status is ok.
    """

    status: str
    detail: str = ""
    uncompressed: Optional[bytes] = None

    @property
    def ok(self) -> bool:
        """True when the gzip member fully decoded and CRC/ISIZE matched."""
        return self.status == GZIP_OK

    def __repr__(self) -> str:
        length = len(self.uncompressed) if self.uncompressed is not None else None
        return (
            f"GzipIntegrity(status={self.status!r}, detail={self.detail!r}, "
            f"uncompressed_len={length})"
        )


def is_compressed_content(data: bytes) -> bool:
    """
    Check if the given data is compressed (gzip or zip) by examining magic bytes.

    This detects compression by content rather than filename, which is important
    because some servers (e.g., KingStore, SuperSapir) return gzip-compressed
    content under filenames that don't end in .gz.

    Args:
        data: The file content to check

    Returns:
        True if the data starts with gzip (0x1f8b) or zip (PK) magic bytes
    """
    if len(data) < 2:
        return False
    return data[:2] in (GZIP_MAGIC_BYTES, ZIP_MAGIC_BYTES)


def validate_gzip_integrity(data: bytes) -> GzipIntegrity:
    """Classify gzip bytes without relying on a generic extract exception.

    Distinguishes a complete valid member from a truncated stream, a CRC/ISIZE
    footer mismatch, and non-gzip content.
    """
    if not data or data[:2] != GZIP_MAGIC_BYTES:
        magic = data[:2].hex() if data else ""
        return GzipIntegrity(
            status=GZIP_NOT_GZIP,
            detail=f"magic bytes: {magic or 'empty'}",
        )

    try:
        uncompressed = gzip.decompress(data)
    except EOFError as exc:
        return GzipIntegrity(status=GZIP_TRUNCATED, detail=str(exc))
    except gzip.BadGzipFile as exc:
        return _classify_gzip_error(str(exc))
    except OSError as exc:
        # gzip may wrap zlib CRC/stream errors as OSError.
        return _classify_gzip_error(str(exc))

    return GzipIntegrity(status=GZIP_OK, uncompressed=uncompressed)


def _classify_gzip_error(message: str) -> GzipIntegrity:
    """Map gzip/zlib error text onto truncated / crc_mismatch / not_gzip."""
    lowered = message.lower()
    if "crc" in lowered or "incorrect length" in lowered or "data check" in lowered:
        return GzipIntegrity(status=GZIP_CRC_MISMATCH, detail=message)
    if "not a gzipped file" in lowered or "incorrect header" in lowered:
        return GzipIntegrity(status=GZIP_NOT_GZIP, detail=message)
    return GzipIntegrity(status=GZIP_TRUNCATED, detail=message)


def extract_xml_from_gz_in_memory(source_file, file_name):
    """Extract xml from gz file or stream"""

    source_buffer = io.BytesIO(source_file)
    output_buffer = io.BytesIO()

    magic_bytes = source_buffer.read(2)
    source_buffer.seek(0)

    if magic_bytes == GZIP_MAGIC_BYTES:
        integrity = validate_gzip_integrity(source_file)
        if not integrity.ok:
            raise ValueError(
                f"gzip {integrity.status}: {file_name}: {integrity.detail} "
                f"(buffer size: {len(source_file)} bytes)"
            )
        output_buffer.write(integrity.uncompressed)
        output_buffer.seek(0)
        return output_buffer.getvalue()

    try:
        if magic_bytes == ZIP_MAGIC_BYTES:
            with zipfile.ZipFile(source_buffer) as the_zip:
                with the_zip.open(the_zip.infolist()[0]) as the_file:
                    shutil.copyfileobj(the_file, output_buffer)
        else:
            raise ValueError(
                f"Unknown compression format. Magic bytes: {magic_bytes.hex()}"
            )

    except Exception as exception:  # pylint: disable=broad-except
        report_failed_zip(exception, source_buffer, file_name)

    output_buffer.seek(0)
    return output_buffer.getvalue()


def report_failed_zip(exception, source_buffer, file_name):
    """Report a file wasn't able to be extracted"""
    try:
        source_buffer.seek(0)
        content = source_buffer.read(1024).decode("utf-8")  # Read first 1KB

        if "link expired" in content.lower():
            raise RestartSessionError()

        raise ValueError(
            f"Error extracting file: {file_name} with error: {str(exception)}, "
            f"buffer size: {source_buffer.getbuffer().nbytes} bytes, "
            f"trimed_file_contant: {content[:100]}"
        )
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"Error extracting file: {file_name} with error: {str(exception)}, "
            f"buffer size: {source_buffer.getbuffer().nbytes} bytes, "
            f"can't decode content"
        ) from exc
