"""Tests for file output configuration."""

import asyncio
import gzip
import os
import tempfile

import pytest

from il_supermarket_scarper.utils import (
    DiskFileOutput,
    QueueFileOutput,
    InMemoryQueueHandler,
    ScraperConfig,
)


class TestFileOutput:
    """Test file output handlers."""

    def test_disk_file_output(self):
        """Test disk file output saves files correctly."""

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                output = DiskFileOutput(tmpdir, extract_gz=False)

                # Test save_file
                result = await output.save_file(
                    file_link="http://example.com/test.xml",
                    file_name="test.xml",
                    file_content=b"<xml>test</xml>",
                    metadata={"chain": "test"},
                )

                assert result["saved"] is True
                assert result["error"] is None
                assert os.path.exists(os.path.join(tmpdir, "test.xml"))

                # Verify file content
                with open(os.path.join(tmpdir, "test.xml"), "rb") as f:
                    content = f.read()
                    assert content == b"<xml>test</xml>"

        asyncio.run(run_test())

    def test_queue_file_output(self):
        """Test queue file output sends to queue correctly."""

        async def run_test():
            handler = InMemoryQueueHandler("test_queue")
            output = QueueFileOutput(handler)

            # Test save_file
            result = await output.save_file(
                file_link="http://example.com/test.xml",
                file_name="test.xml",
                file_content=b"<xml>test</xml>",
                metadata={"chain": "test"},
            )

            assert result["saved"] is True
            assert result["error"] is None

            # Verify message was sent
            message_count = 0
            async for message in handler.get_all_messages():
                message_count += 1
                assert message["file_name"] == "test.xml"
                assert message["file_content"] == b"<xml>test</xml>"
                assert message["metadata"]["chain"] == "test"
                break  # Only check first message
            assert message_count == 1
            await handler.close()

        asyncio.run(run_test())

    def test_queue_file_output_extracts_gzip_without_extension(self):
        """Test queue output extracts gzip content without .gz extension."""

        async def run_test():
            handler = InMemoryQueueHandler("test_queue")
            output = QueueFileOutput(handler, extract_gz=True)

            xml_content = b"<xml>test content</xml>"
            gzip_content = gzip.compress(xml_content)

            result = await output.save_file(
                file_link="http://example.com/Stores7290058108879-000",
                file_name="Stores7290058108879-000",
                file_content=gzip_content,
                metadata={"chain": "KingStore"},
            )

            assert result["saved"] is True
            assert result["extract_successfully"] is True
            assert result["file_name"] == "Stores7290058108879-000.xml"

            # Verify extracted content was sent
            async for message in handler.get_all_messages():
                assert message["file_name"] == "Stores7290058108879-000.xml"
                assert message["file_content"] == xml_content
                break
            await handler.close()

        asyncio.run(run_test())

    def test_queue_file_output_respects_extract_gz_false(self):
        """Test queue output preserves compressed content when extract_gz=False."""

        async def run_test():
            handler = InMemoryQueueHandler("test_queue")
            output = QueueFileOutput(handler, extract_gz=False)

            xml_content = b"<xml>test content</xml>"
            gzip_content = gzip.compress(xml_content)

            result = await output.save_file(
                file_link="http://example.com/test.xml.gz",
                file_name="test.xml.gz",
                file_content=gzip_content,
                metadata={"chain": "test"},
            )

            assert result["saved"] is True
            assert result["file_name"] == "test.xml.gz"

            # Verify compressed content was sent
            async for message in handler.get_all_messages():
                assert message["file_name"] == "test.xml.gz"
                assert message["file_content"] == gzip_content
                break
            await handler.close()

        asyncio.run(run_test())

    def test_scraper_config_defaults(self):
        """Test ScraperConfig default values."""
        config = ScraperConfig()

        assert config.filter_null is True
        assert config.filter_zero is True
        assert config.min_size == 100
        assert config.max_size == 10_000_000
        assert config.folder_name is None
        assert config.file_output is None

    def test_scraper_config_disk_output(self):
        """Test ScraperConfig with disk output using folder_name."""
        config = ScraperConfig.disk(
            folder_name="my_output",
            filter_null=False,
            min_size=1000,
        )

        assert config.folder_name == "my_output"
        assert config.file_output is None  # Will be created on demand
        assert config.filter_null is False
        assert config.min_size == 1000
        assert config.is_disk_output() is True
        assert config.is_queue_output() is False

    def test_scraper_config_queue_output(self):
        """Test ScraperConfig with queue output."""
        handler = InMemoryQueueHandler("custom")
        queue_output = QueueFileOutput(handler)

        config = ScraperConfig.queue(
            file_output=queue_output,
            filter_null=False,
            min_size=1000,
        )

        assert config.file_output is queue_output
        assert config.filter_null is False
        assert config.min_size == 1000
        assert config.is_disk_output() is False
        assert config.is_queue_output() is True

    def test_scraper_config_get_file_output(self):
        """Test ScraperConfig.get_file_output method."""
        # Test with folder_name
        config = ScraperConfig(folder_name="test_output")
        output = config.get_file_output("TestChain")
        assert isinstance(output, DiskFileOutput)
        assert "test_output" in output.get_output_location()

        # Test with file_output
        handler = InMemoryQueueHandler("test")
        config = ScraperConfig(file_output=QueueFileOutput(handler))
        output = config.get_file_output("TestChain")
        assert isinstance(output, QueueFileOutput)
        assert "memory:test" in output.get_output_location()

    def test_get_output_location(self):
        """Test output location strings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            disk = DiskFileOutput(tmpdir)
            assert disk.get_output_location() == f"disk:{tmpdir}"

        handler = InMemoryQueueHandler("myqueue")
        queue = QueueFileOutput(handler)
        assert queue.get_output_location() == "queue:memory:myqueue"

    def test_disk_output_extracts_gzip_with_gz_extension(self):
        """Test that gzip files with .gz extension are extracted."""

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                output = DiskFileOutput(tmpdir, extract_gz=True)

                xml_content = b"<xml>test content</xml>"
                gzip_content = gzip.compress(xml_content)

                result = await output.save_file(
                    file_link="http://example.com/test.xml.gz",
                    file_name="test.xml.gz",
                    file_content=gzip_content,
                    metadata={"chain": "test"},
                )

                assert result["saved"] is True
                assert result["extract_successfully"] is True
                assert result["file_name"] == "test.xml"
                assert os.path.exists(os.path.join(tmpdir, "test.xml"))

                with open(os.path.join(tmpdir, "test.xml"), "rb") as f:
                    content = f.read()
                    assert content == xml_content

        asyncio.run(run_test())

    def test_disk_output_extracts_gzip_without_gz_extension(self):
        """Test that gzip files WITHOUT .gz extension are still extracted.

        This is the bug fix for KingStore/SuperSapir where servers return
        gzip-compressed content under filenames that don't end in .gz.
        """

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                output = DiskFileOutput(tmpdir, extract_gz=True)

                xml_content = b"<xml>test content</xml>"
                gzip_content = gzip.compress(xml_content)

                result = await output.save_file(
                    file_link="http://example.com/Stores7290058108879-000",
                    file_name="Stores7290058108879-000",
                    file_content=gzip_content,
                    metadata={"chain": "KingStore"},
                )

                assert result["saved"] is True
                assert result["extract_successfully"] is True
                assert result["file_name"] == "Stores7290058108879-000.xml"
                assert os.path.exists(
                    os.path.join(tmpdir, "Stores7290058108879-000.xml")
                )

                with open(
                    os.path.join(tmpdir, "Stores7290058108879-000.xml"), "rb"
                ) as f:
                    content = f.read()
                    assert content == xml_content

        asyncio.run(run_test())

    def test_disk_output_does_not_extract_uncompressed_content(self):
        """Test that uncompressed content is saved as-is."""

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                output = DiskFileOutput(tmpdir, extract_gz=True)

                xml_content = b"<xml>test content</xml>"

                result = await output.save_file(
                    file_link="http://example.com/test.xml",
                    file_name="test.xml",
                    file_content=xml_content,
                    metadata={"chain": "test"},
                )

                assert result["saved"] is True
                assert result["extract_successfully"] is True
                assert result["file_name"] == "test.xml"

                with open(os.path.join(tmpdir, "test.xml"), "rb") as f:
                    content = f.read()
                    assert content == xml_content

        asyncio.run(run_test())

    def test_disk_output_respects_extract_gz_false(self):
        """Test that extract_gz=False preserves compressed content."""

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                output = DiskFileOutput(tmpdir, extract_gz=False)

                xml_content = b"<xml>test content</xml>"
                gzip_content = gzip.compress(xml_content)

                result = await output.save_file(
                    file_link="http://example.com/test.xml.gz",
                    file_name="test.xml.gz",
                    file_content=gzip_content,
                    metadata={"chain": "test"},
                )

                assert result["saved"] is True
                assert result["file_name"] == "test.xml.gz"

                with open(os.path.join(tmpdir, "test.xml.gz"), "rb") as f:
                    content = f.read()
                    assert content == gzip_content

        asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
