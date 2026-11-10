"""Tests for bounded concurrent listing/work overlap."""

import asyncio
import threading
import time
import unittest

from il_supermarket_scarper.utils.core.async_work import (
    run_in_daemon_thread,
    stream_as_completed,
)


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


class TestRunInDaemonThread(unittest.IsolatedAsyncioTestCase):
    """Cancelling the await must not leave the caller waiting on the thread."""

    async def test_returns_result_and_passes_cancel_event(self):
        """A normal call returns the function result."""

        def func(value, cancel_event=None):
            assert not cancel_event.is_set()
            return value * 2

        self.assertEqual(await run_in_daemon_thread(func, 21), 42)

    async def test_propagates_exception(self):
        """Errors from the thread surface to the awaiting task."""

        def func(cancel_event=None):  # pylint: disable=unused-argument
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            await run_in_daemon_thread(func)

    async def test_cancel_sets_event_and_returns_immediately(self):
        """Cancelling sets the event; the slow thread does not block the caller."""
        started = threading.Event()
        seen = {}

        def func(cancel_event=None):
            started.set()
            seen["event"] = cancel_event
            cancel_event.wait(timeout=30)  # stands in for a hung request
            return "late"

        task = asyncio.create_task(run_in_daemon_thread(func))
        await asyncio.to_thread(started.wait, 5)
        begin = time.monotonic()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertLess(time.monotonic() - begin, 1)
        self.assertTrue(seen["event"].is_set())
