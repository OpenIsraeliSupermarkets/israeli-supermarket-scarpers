import asyncio
import gzip
import io
import os
import shutil
import zipfile
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

from il_supermarket_scarper.utils.core.exceptions import RestartSessionError
from il_supermarket_scarper.utils.core.logger import Logger

GZIP_MAGIC_BYTES = b"\x1f\x8b"
ZIP_MAGIC_BYTES = b"PK"


class GzipStatus(str, Enum):
    """Outcome of validating a gzip member."""

    OK = "ok"
    TRUNCATED = "truncated"
    CRC_MISMATCH = "crc_mismatch"
    NOT_GZIP = "not_gzip"


# Backward-compatible aliases
GZIP_OK = GzipStatus.OK
GZIP_TRUNCATED = GzipStatus.TRUNCATED
GZIP_CRC_MISMATCH = GzipStatus.CRC_MISMATCH
GZIP_NOT_GZIP = GzipStatus.NOT_GZIP


@dataclass(frozen=True)
class GzipIntegrity:
    """gzip member completeness + footer check.

    ``uncompressed`` is set only when status is ``GzipStatus.OK``.
    """

    status: GzipStatus
    detail: str = ""
    uncompressed: Optional[bytes] = None

    @property
    def ok(self) -> bool:
        """True when the gzip member fully decoded and CRC/ISIZE matched."""
        return self.status is GzipStatus.OK

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


async def extract_if_compressed(
    file_content: bytes, file_name: str, extract_gz: bool = True
) -> Tuple[bytes, str, bool, Optional[str]]:
    """Extract compressed content if needed.

    Detects compression by content magic bytes (gzip: 0x1f8b, zip: PK)
    rather than filename extension.

    Returns:
        (content, filename, extraction_success, error)
    """
    if not extract_gz or not is_compressed_content(file_content):
        return file_content, file_name, True, None

    try:
        extracted = await asyncio.to_thread(
            extract_xml_from_gz_in_memory, file_content, file_name
        )
        base_name = file_name[:-3] if file_name.endswith(".gz") else file_name
        new_name = os.path.splitext(base_name)[0] + ".xml"
        return extracted, new_name, True, None
    except Exception as e:  # pylint: disable=broad-except
        Logger.error(f"Failed to extract {file_name}: {e}")
        return file_content, file_name, False, str(e)


def validate_gzip_integrity(data: bytes) -> GzipIntegrity:
    """Classify gzip bytes without relying on a generic extract exception.

    Distinguishes a complete valid member from a truncated stream, a CRC/ISIZE
    footer mismatch, and non-gzip content.
    """
    if not data or data[:2] != GZIP_MAGIC_BYTES:
        magic = data[:2].hex() if data else ""
        return GzipIntegrity(
            status=GzipStatus.NOT_GZIP,
            detail=f"magic bytes: {magic or 'empty'}",
        )

    try:
        uncompressed = gzip.decompress(data)
    except EOFError as exc:
        return GzipIntegrity(status=GzipStatus.TRUNCATED, detail=str(exc))
    except gzip.BadGzipFile as exc:
        return _classify_gzip_error(str(exc))
    except OSError as exc:
        # gzip may wrap zlib CRC/stream errors as OSError.
        return _classify_gzip_error(str(exc))

    return GzipIntegrity(status=GzipStatus.OK, uncompressed=uncompressed)


def _classify_gzip_error(message: str) -> GzipIntegrity:
    """Map gzip/zlib error text onto truncated / crc_mismatch / not_gzip."""
    lowered = message.lower()
    if "crc" in lowered or "incorrect length" in lowered or "data check" in lowered:
        return GzipIntegrity(status=GzipStatus.CRC_MISMATCH, detail=message)
    if "not a gzipped file" in lowered or "incorrect header" in lowered:
        return GzipIntegrity(status=GzipStatus.NOT_GZIP, detail=message)
    return GzipIntegrity(status=GzipStatus.TRUNCATED, detail=message)


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
                f"gzip {integrity.status.value}: {file_name}: {integrity.detail} "
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
