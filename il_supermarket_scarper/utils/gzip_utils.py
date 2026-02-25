import gzip
import shutil
import io
import zipfile
from .exceptions import RestartSessionError

GZIP_MAGIC_BYTES = b'\x1f\x8b'
ZIP_MAGIC_BYTES = b'PK'

def extract_xml_from_gz_in_memory(source_file, file_name):
    """Extract xml from gz file or stream"""

    source_buffer = io.BytesIO(source_file)
    output_buffer = io.BytesIO()

    magic_bytes = source_buffer.read(2)
    source_buffer.seek(0)

    try:
        if magic_bytes == GZIP_MAGIC_BYTES:
            with gzip.open(source_buffer, "rb") as infile:
                shutil.copyfileobj(infile, output_buffer)

        elif magic_bytes == ZIP_MAGIC_BYTES:
            with zipfile.ZipFile(source_buffer) as the_zip:
                with the_zip.open(the_zip.infolist()[0]) as the_file:
                    shutil.copyfileobj(the_file, output_buffer)
        else:
            raise ValueError(f"Unknown compression format. Magic bytes: {magic_bytes.hex()}")

    except Exception as exception:  # pylint: disable=broad-except
        report_failed_zip(exception, source_buffer, file_name)

    output_buffer.seek(0)
    return output_buffer.getvalue()

def report_failed_zip(exception, source_buffer, file_name):
    """Report a file wasn't able to be extracted"""
    try:
        source_buffer.seek(0)
        content = source_buffer.read(1024).decode('utf-8')  # Read first 1KB

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
