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
from il_supermarket_scarper.utils.file_output import content_sha256
from il_supermarket_scarper.utils.gzip_utils import extract_if_compressed
from il_supermarket_scarper.utils.save_policy import SaveDecision, SavePolicy
from il_supermarket_scarper.utils.verified_downloads import VerifiedDownloads
from il_supermarket_scarper.utils.databases import JsonDataBase


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
            content, name, ok, err = await extract_if_compressed(
                gzip_content, "Stores7290058108879-000", extract_gz=True
            )
            assert ok is True
            assert err is None
            result = await output.save_file(
                file_link="http://example.com/Stores7290058108879-000",
                file_name=name,
                file_content=content,
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
                content, name, ok, err = await extract_if_compressed(
                    gzip_content, "test.xml.gz", extract_gz=True
                )
                assert ok is True and err is None
                result = await output.save_file(
                    file_link="http://example.com/test.xml.gz",
                    file_name=name,
                    file_content=content,
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
                content, name, ok, err = await extract_if_compressed(
                    gzip_content, "Stores7290058108879-000", extract_gz=True
                )
                assert ok is True and err is None
                result = await output.save_file(
                    file_link="http://example.com/Stores7290058108879-000",
                    file_name=name,
                    file_content=content,
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

    def test_disk_output_reports_gzip_truncated(self):
        """Extract failure surfaces gzip truncated instead of a blank error."""

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                output = DiskFileOutput(tmpdir, extract_gz=True)
                truncated = gzip.compress(b"<xml>test content</xml>")[:-20]
                _content, _name, ok, err = await extract_if_compressed(
                    truncated, "test.xml.gz", extract_gz=True
                )
                assert ok is False
                assert err
                assert "gzip truncated" in err

        asyncio.run(run_test())

    def test_disk_output_always_writes_when_called(self):
        """FileOutput always persists; SavePolicy decides whether to call it."""

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                output = DiskFileOutput(tmpdir, extract_gz=False)
                payload = b"<xml>same</xml>"
                first = await output.save_file(
                    file_link="http://example.com/a.xml",
                    file_name="PromoFull7290-001.xml",
                    file_content=payload,
                )
                writes = {"n": 0}
                original_write = output._write_file  # pylint: disable=protected-access

                def counted_write(file_path, content):
                    writes["n"] += 1
                    original_write(file_path, content)

                output._write_file = counted_write  # pylint: disable=protected-access
                second = await output.save_file(
                    file_link="http://example.com/a.xml",
                    file_name="PromoFull7290-001.xml",
                    file_content=payload,
                )
                assert first["saved"] is True
                assert second["saved"] is True
                assert writes["n"] == 1
                assert os.listdir(tmpdir) == ["PromoFull7290-001.xml"]

        asyncio.run(run_test())

    def test_disk_output_overwrites_on_second_call(self):
        """A second save_file call overwrites under the original name."""

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                output = DiskFileOutput(tmpdir, extract_gz=False)
                first_bytes = b"<xml>one</xml>"
                second_bytes = b"<xml>two</xml>"
                first = await output.save_file(
                    file_link="http://example.com/a.xml",
                    file_name="PromoFull7290-001.xml",
                    file_content=first_bytes,
                )
                second = await output.save_file(
                    file_link="http://example.com/b.xml",
                    file_name="PromoFull7290-001.xml",
                    file_content=second_bytes,
                )
                assert first["file_name"] == second["file_name"] == "PromoFull7290-001.xml"
                assert second["content_sha256"] == content_sha256(second_bytes)
                assert os.listdir(tmpdir) == ["PromoFull7290-001.xml"]
                with open(os.path.join(tmpdir, "PromoFull7290-001.xml"), "rb") as f:
                    assert f.read() == second_bytes

        asyncio.run(run_test())

    def test_save_policy_skips_persist_on_rewrote_same(self):
        """SavePolicy gates writes; FileOutput is not called for same hash."""

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                db = JsonDataBase("fo_policy", tmpdir)
                verified = VerifiedDownloads(db)
                policy = SavePolicy(verified)
                payload = b"<xml>same</xml>"
                digest = content_sha256(payload)
                calls = {"n": 0}

                async def persist(_decision):
                    calls["n"] += 1

                first = await policy.decide_and_persist(
                    "PromoFull7290-001.xml",
                    digest,
                    "2026-09-08T14:00:00",
                    persist,
                    listing_hash="lh1",
                )
                second = await policy.decide_and_persist(
                    "PromoFull7290-001.xml",
                    digest,
                    "2026-09-08T15:00:00",
                    persist,
                    listing_hash="lh2",
                )
                assert first == SaveDecision.CREATED
                assert second == SaveDecision.REWROTE_SAME
                assert calls["n"] == 1

        asyncio.run(run_test())

    def test_save_policy_skips_persist_on_stale_older(self):
        """STALE_OLDER does not invoke the persist callback."""

        async def run_test():
            with tempfile.TemporaryDirectory() as tmpdir:
                db = JsonDataBase("fo_stale", tmpdir)
                verified = VerifiedDownloads(db)
                policy = SavePolicy(verified)
                calls = {"n": 0}

                async def persist(_decision):
                    calls["n"] += 1

                await policy.decide_and_persist(
                    "PromoFull7290-001.xml",
                    "newdigest",
                    "2026-09-08T14:00:00",
                    persist,
                    listing_hash="lh1",
                )
                older = await policy.decide_and_persist(
                    "PromoFull7290-001.xml",
                    "olddigest",
                    "2026-09-08T10:00:00",
                    persist,
                    listing_hash="lh2",
                )
                assert older == SaveDecision.STALE_OLDER
                assert calls["n"] == 1

        asyncio.run(run_test())

    def test_queue_output_always_sends_when_called(self):
        """QueueFileOutput sends on every save_file call."""

        async def run_test():
            handler = InMemoryQueueHandler("same_bytes")
            output = QueueFileOutput(handler, extract_gz=False)
            payload = b"<xml>same</xml>"
            first = await output.save_file(
                file_link="http://example.com/a.xml",
                file_name="PromoFull7290-001.xml",
                file_content=payload,
            )
            second = await output.save_file(
                file_link="http://example.com/a.xml",
                file_name="PromoFull7290-001.xml",
                file_content=payload,
            )
            assert first["saved"] is True
            assert second["saved"] is True
            assert first["file_name"] == second["file_name"] == "PromoFull7290-001.xml"
            await handler.close()
            names = []
            async for message in handler.get_all_messages():
                names.append(message["file_name"])
            assert names == ["PromoFull7290-001.xml", "PromoFull7290-001.xml"]

        asyncio.run(run_test())

    def test_queue_output_pushes_different_bytes_under_same_name(self):
        """Different content is queued again under the original file name."""

        async def run_test():
            handler = InMemoryQueueHandler("conflict")
            output = QueueFileOutput(handler, extract_gz=False)
            first_bytes = b"<xml>one</xml>"
            second_bytes = b"<xml>two</xml>"
            first = await output.save_file(
                file_link="http://example.com/a.xml",
                file_name="PromoFull7290-001.xml",
                file_content=first_bytes,
            )
            second = await output.save_file(
                file_link="http://example.com/b.xml",
                file_name="PromoFull7290-001.xml",
                file_content=second_bytes,
            )
            assert first["file_name"] == second["file_name"] == "PromoFull7290-001.xml"
            assert second["content_sha256"] == content_sha256(second_bytes)
            await output.close()
            payloads = []
            async for message in handler.get_all_messages():
                payloads.append((message["file_name"], message["file_content"]))
            assert payloads == [
                ("PromoFull7290-001.xml", first_bytes),
                ("PromoFull7290-001.xml", second_bytes),
            ]

        asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
