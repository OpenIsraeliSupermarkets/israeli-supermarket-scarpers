"""Tests for bounded concurrent listing/work overlap."""

import asyncio
import unittest

from il_supermarket_scarper.utils.async_work import stream_as_completed


class TestStreamAsCompleted(unittest.IsolatedAsyncioTestCase):
    """Verify failed work or listing does not hide siblings that already finished."""

    async def test_failed_work_does_not_drop_completed_sibling(self):
        """A boom on one item must not prevent yielding other finished items."""

        async def source():
            yield "fast"
            yield "fail"
            yield "other"

        async def work(item):
            if item == "fail":
                raise RuntimeError("boom")
            return [item]

        results = []
        gen = stream_as_completed(source(), work, max_in_flight=3)
        try:
            async for item in gen:
                results.append(item)
        finally:
            await gen.aclose()

        self.assertEqual(set(results), {"fast", "other"})

    async def test_source_error_still_yields_completed_work(self):
        """A listing error after the first item must still yield that download."""

        async def source():
            yield "a"
            raise RuntimeError("listing died")

        async def work(item):
            await asyncio.sleep(0.05)
            return [item]

        results = []
        gen = stream_as_completed(source(), work, max_in_flight=2)
        try:
            async for item in gen:
                results.append(item)
        finally:
            await gen.aclose()

        self.assertEqual(results, ["a"])

    async def test_yields_first_result_before_source_is_exhausted(self):
        """Work on the first item must complete while later listing is blocked."""
        release = asyncio.Event()

        async def source():
            yield "first"
            await release.wait()
            yield "second"

        async def work(item):
            return [item]

        gen = stream_as_completed(source(), work, max_in_flight=2)
        try:
            first = await asyncio.wait_for(anext(gen), timeout=1)
            self.assertEqual(first, "first")
            self.assertFalse(release.is_set())
            release.set()
            rest = [item async for item in gen]
        finally:
            await gen.aclose()

        self.assertEqual(rest, ["second"])
