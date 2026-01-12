"""Tests for file output configuration."""

import asyncio
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
            messages = handler.get_all_messages()
            assert len(messages) == 1
            assert messages[0]["file_name"] == "test.xml"
            assert messages[0]["file_content"] == b"<xml>test</xml>"
            assert messages[0]["metadata"]["chain"] == "test"

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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
