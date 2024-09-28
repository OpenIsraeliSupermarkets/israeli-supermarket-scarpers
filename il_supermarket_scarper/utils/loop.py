import concurrent.futures


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


def execute_in_parallels(
    function_to_execute,
    iterable,
    max_workers=None,
    aggregtion_function=defualt_aggregtion_function,
):
    """execute a job in the event loop"""

    results = run_tasks(
        function_to_execute,
        iterable,
        max_workers=max_workers,
    )
    
    all_done = aggregtion_function(results)
    print(f"Done with {len(all_done)} tasks")
    return all_done

def run_tasks(
    function_to_execute,
    iterable,
    max_workers: int = None,
):
    """Run tasks in multi-thread or sequentially"""
    if max_workers:
        # Use multi-thread
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(function_to_execute, arg) for arg in iterable]
            return [future.result() for future in concurrent.futures.as_completed(futures)]
    else:
        # Or just iterate over all
        return [function_to_execute(arg) for arg in iterable]