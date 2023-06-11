import asyncio
import concurrent.futures
from .logger import Logger


def get_event_loop():
    """get the current running event loop"""
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def defualt_aggregtion_function(all_done):
    """format the scraping result to the final input"""
    result = []
    for response in all_done:
        _response = response
        if hasattr(_response, "result"):
            _response = _response.result()
        result.append(_response)
    return result


def multiple_page_aggregtion(pages_to_scrape):
    """format the scraping result to the final input for multipage"""
    download_urls = []
    file_names = []
    for result in pages_to_scrape:
        page_download_urls, page_file_names = result.result()
        download_urls.extend(page_download_urls)
        file_names.extend(page_file_names)
    return download_urls, file_names


def execute_in_event_loop(
    function_to_execute,
    iterable,
    max_workers=None,
    aggregtion_function=defualt_aggregtion_function,
):
    """execute a job in the event loop"""

    loop = get_event_loop()
    return loop.run_until_complete(
        run_task_async(
            function_to_execute,
            iterable,
            max_workers=max_workers,
            aggregtion_function=aggregtion_function,
        )
    )


async def run_task_async(
    function_to_execute,
    iterable,
    max_workers=None,
    aggregtion_function=defualt_aggregtion_function,
):
    """run task in multi-thread"""
    loop = get_event_loop()

    if max_workers:
        # use multi-thread
        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            for arg in iterable:
                futures.append(loop.run_in_executor(executor, function_to_execute, arg))

        if len(futures) == 0:
            return []
        all_done, not_done = await asyncio.wait(futures)
        assert len(not_done) == 0, "Not all tasks are done, should be blocking."
    else:
        # or just itreate over all
        all_done = []
        for arg in iterable:
            all_done.append(function_to_execute(arg))
    all_done = aggregtion_function(list(all_done))

    Logger.info(f"Done with {len(all_done)} files")
    return all_done
