"""Bounded concurrent pull from an async source with overlapping work."""

import asyncio
from il_supermarket_scarper.utils.logger import Logger


def _unpack_result(result):
    """Yield a list's items, or the result itself when it is a single value."""
    if result is None:
        return
    if isinstance(result, list):
        yield from result
        return
    yield result


def _default_error(prefix, error):
    Logger.error(f"{prefix}: {error}")
    Logger.error_execption(error)


async def stream_as_completed(  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    source,
    start_work,
    max_in_flight,
    *,
    accept_item=bool,
    source_error_prefix="Error reading listing",
    work_error_prefix="Error processing item",
    on_source_error=None,
    on_work_error=None,
):
    """Yield work results as they finish, without waiting to fill the pool.

    Pulls items from ``source`` and runs ``start_work(item)`` with at most
    ``max_in_flight`` tasks. Listing and work wait together so the first
    completed result is not blocked on more source items.

    A failed source pull stops further listing but still drains in-flight
    work. A failed work task is logged and skipped so siblings in the same
    wait batch are still yielded. More listing is scheduled before yielding
    so the next site/page stays in flight while the consumer is busy.
    """
    handle_source_error = on_source_error or (
        lambda error: _default_error(source_error_prefix, error)
    )
    handle_work_error = on_work_error or (
        lambda error: _default_error(work_error_prefix, error)
    )

    listing_done = object()
    pending = set()
    source_exhausted = False
    listing_task = None

    async def next_source_item():
        try:
            return await anext(source)
        except StopAsyncIteration:
            return listing_done

    def apply_source_item(source_item):
        """Start work for a source item. Return True if listing is exhausted."""
        if source_item is listing_done:
            return True
        if accept_item(source_item):
            pending.add(asyncio.create_task(start_work(source_item)))
        return False

    async def refill():
        """Start more listing/work if a source item is already available."""
        nonlocal listing_task, source_exhausted
        while not source_exhausted and len(pending) < max_in_flight:
            if listing_task is None:
                listing_task = asyncio.create_task(next_source_item())
            await asyncio.sleep(0)
            if not listing_task.done():
                return
            try:
                source_item = listing_task.result()
            except Exception as error:  # pylint: disable=broad-exception-caught
                handle_source_error(error)
                listing_task = None
                source_exhausted = True
                return
            listing_task = None
            source_exhausted = apply_source_item(source_item)

    try:
        while True:
            await refill()

            wait_for = set(pending)
            if listing_task is not None:
                wait_for.add(listing_task)
            if not wait_for:
                break

            done, _pending = await asyncio.wait(
                wait_for, return_when=asyncio.FIRST_COMPLETED
            )

            completed_items = []
            for task in done:
                if task not in pending:
                    continue
                pending.remove(task)
                try:
                    result = task.result()
                except Exception as error:  # pylint: disable=broad-exception-caught
                    handle_work_error(error)
                    continue
                completed_items.extend(_unpack_result(result))

            if listing_task is not None and listing_task in done:
                try:
                    source_item = listing_task.result()
                except Exception as error:  # pylint: disable=broad-exception-caught
                    handle_source_error(error)
                    listing_task = None
                    source_exhausted = True
                else:
                    listing_task = None
                    source_exhausted = apply_source_item(source_item)

            # Keep listing ahead of the consumer before yielding.
            await refill()

            for item in completed_items:
                yield item
    finally:
        if listing_task is not None:
            listing_task.cancel()
            await asyncio.gather(listing_task, return_exceptions=True)
        await source.aclose()
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
