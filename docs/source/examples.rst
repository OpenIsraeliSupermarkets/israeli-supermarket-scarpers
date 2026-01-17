Examples
========

This page provides practical examples for common use cases.

Basic Scraping
--------------

Simple scraping task:

.. code-block:: python

    from il_supermarket_scarper import ScarpingTask

    scraper = ScarpingTask()
    scraper.start()
    scraper.join()

Scraping Specific Chains
------------------------

Scrape only specific supermarket chains:

.. code-block:: python

    from il_supermarket_scarper import ScarpingTask
    from il_supermarket_scarper.scrappers_factory import ScraperFactory

    scraper = ScarpingTask(
        enabled_scrapers=[
            ScraperFactory.WOLT,
            ScraperFactory.YAYNO_BITAN,
            ScraperFactory.SHUFERSAL
        ]
    )
    scraper.start(limit=50)
    scraper.join()

File Type Filtering
-------------------

Download only specific file types:

.. code-block:: python

    from il_supermarket_scarper import ScarpingTask, FileTypesFilters

    # Only price files
    scraper = ScarpingTask(
        files_types=FileTypesFilters.PRICE_FILE
    )
    scraper.start()

    # Multiple file types
    scraper = ScarpingTask(
        files_types=[
            FileTypesFilters.STORE_FILE,
            FileTypesFilters.PRICE_FILE
        ]
    )
    scraper.start()

Size Filtering
--------------

Filter files by size:

.. code-block:: python

    scraper = ScarpingTask(
        min_size=1000,      # Minimum 1KB
        max_size=10_000_000  # Maximum 10MB
    )
    scraper.start()

Date-Based Scraping
-------------------

Scrape files from a specific date:

.. code-block:: python

    from datetime import datetime

    scraper = ScarpingTask()
    scraper.start(
        when_date=datetime(2024, 10, 23, 14, 35)
    )
    scraper.join()

Custom Output Directory
-----------------------

Save files to a custom directory:

.. code-block:: python

    from il_supermarket_scarper.scrappers_factory import ScraperFactory
    import asyncio

    scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
    scraper = scraper_class(folder_name="custom_output")

    async def run():
        await scraper.scrape(limit=10)

    asyncio.run(run())

Queue Output
------------

Use queue-based output instead of disk:

.. code-block:: python

    from il_supermarket_scarper.scrappers_factory import ScraperFactory
    from il_supermarket_scarper.utils import QueueFileOutput, InMemoryQueueHandler
    import asyncio

    # Create queue handler
    queue = InMemoryQueueHandler("scraper_queue")
    output = QueueFileOutput(queue)

    # Create scraper with queue output
    scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
    scraper = scraper_class(file_output=output)

    async def run():
        await scraper.scrape(limit=5)
        
        # Process messages from queue
        messages = queue.get_all_messages()
        for msg in messages:
            print(f"Received: {msg}")

    asyncio.run(run())

Unified Configuration
---------------------

Use ScraperConfig for comprehensive settings:

.. code-block:: python

    from il_supermarket_scarper.scrappers_factory import ScraperFactory
    from il_supermarket_scarper.utils import ScraperConfig
    import asyncio

    # Create unified config
    config = ScraperConfig.disk(
        folder_name="production_output",
        filter_null=True,
        filter_zero=True,
        min_size=1000,
        max_size=5_000_000,
        metadata={"environment": "prod"}
    )

    # Use with scraper
    scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
    scraper = scraper_class(
        folder_name=config.get_folder_name(),
        file_output=config.get_file_output("Wolt")
    )

    async def run():
        await scraper.scrape(
            limit=10,
            filter_null=config.filter_null,
            filter_zero=config.filter_zero,
            min_size=config.min_size,
            max_size=config.max_size
        )

    asyncio.run(run())

Processing Results
------------------

Process results as they become available:

.. code-block:: python

    from il_supermarket_scarper import ScarpingTask

    scraper = ScarpingTask()
    scraper.start(limit=20)

    # Process results
    for result in scraper.consume():
        if result.extract_succefully:
            print(f"✓ Successfully downloaded: {result.file_name}")
        else:
            print(f"✗ Failed: {result.file_name}")
            if result.error:
                print(f"  Error: {result.error}")

    scraper.join()

Docker Examples
---------------

Basic Docker usage:

.. code-block:: bash

    docker run -v "./dumps:/usr/src/app/dumps" \
               -e ENABLED_SCRAPERS="WOLT,YAYNO_BITAN" \
               -e ENABLED_FILE_TYPES="STORE_FILE" \
               -e LIMIT=10 \
               erlichsefi/israeli-supermarket-scarpers

With custom date:

.. code-block:: bash

    docker run -v "./dumps:/usr/src/app/dumps" \
               -e ENABLED_SCRAPERS="WOLT" \
               -e TODAY="2024-10-23 14:35" \
               erlichsefi/israeli-supermarket-scarpers

Queue output mode:

.. code-block:: bash

    docker run -e OUTPUT_MODE="queue" \
               -e QUEUE_TYPE="memory" \
               -e ENABLED_SCRAPERS="WOLT" \
               erlichsefi/israeli-supermarket-scarpers

Kafka queue output:

.. code-block:: bash

    docker run -e OUTPUT_MODE="queue" \
               -e QUEUE_TYPE="kafka" \
               -e KAFKA_BOOTSTRAP_SERVERS="localhost:9092" \
               -e ENABLED_SCRAPERS="WOLT" \
               erlichsefi/israeli-supermarket-scarpers

Advanced: Async Scraping
------------------------

For more control, use the async API directly:

.. code-block:: python

    from il_supermarket_scarper.scrappers_factory import ScraperFactory
    import asyncio

    async def scrape_multiple_chains():
        chains = [
            ScraperFactory.WOLT,
            ScraperFactory.YAYNO_BITAN,
            ScraperFactory.SHUFERSAL
        ]
        
        tasks = []
        for chain in chains:
            scraper_class = ScraperFactory.get(chain)
            scraper = scraper_class(folder_name=f"output_{chain.name}")
            tasks.append(scraper.scrape(limit=5))
        
        # Run all scrapers concurrently
        await asyncio.gather(*tasks)

    asyncio.run(scrape_multiple_chains())

Error Handling
--------------

Handle errors gracefully:

.. code-block:: python

    from il_supermarket_scarper import ScarpingTask

    scraper = ScarpingTask(
        timeout_in_seconds=300  # 5 minutes timeout
    )

    try:
        scraper.start(limit=100)
        scraper.join()
    except RuntimeError as e:
        print(f"Scraping error: {e}")
    finally:
        scraper.stop()

For more configuration options, see :ref:`configuration`.
