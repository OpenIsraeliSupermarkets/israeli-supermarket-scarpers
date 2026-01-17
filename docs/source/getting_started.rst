Getting Started
===============

This guide will help you get started with ``il-supermarket-scraper`` quickly.

Installation
------------

Install from PyPI:

.. code-block:: bash

    pip install il-supermarket-scraper

Or install the latest version directly from GitHub:

.. code-block:: bash

    pip install -U git+https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers.git

For development, clone the repository and install in editable mode:

.. code-block:: bash

    git clone https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers.git
    cd israeli-supermarket-scarpers
    pip install -r requirements-dev.txt
    pip install -e .

Quick Start
-----------

The simplest way to use the scraper is to create a ``ScarpingTask`` and start it:

.. code-block:: python

    from il_supermarket_scarper import ScarpingTask

    scraper = ScarpingTask()
    scraper.start()

This will download all available files from all supported supermarket chains.

Basic Usage
-----------

Scraping a Single Chain
~~~~~~~~~~~~~~~~~~~~~~~

To scrape a specific supermarket chain:

.. code-block:: python

    from il_supermarket_scarper import ScarpingTask
    from il_supermarket_scarper.scrappers_factory import ScraperFactory

    # Create task with specific scrapers enabled
    scraper = ScarpingTask(
        enabled_scrapers=[ScraperFactory.WOLT]
    )
    scraper.start()
    scraper.join()  # Wait for completion

Limiting Files
~~~~~~~~~~~~~~

Limit the number of files to download:

.. code-block:: python

    scraper = ScarpingTask()
    scraper.start(limit=10)  # Download only 10 files
    scraper.join()

Filtering File Types
~~~~~~~~~~~~~~~~~~~~

Download only specific file types:

.. code-block:: python

    from il_supermarket_scarper import ScarpingTask, FileTypesFilters

    scraper = ScarpingTask(
        files_types=FileTypesFilters.STORE_FILE  # Only store files
    )
    scraper.start()

Custom Output Directory
~~~~~~~~~~~~~~~~~~~~~~~

Specify a custom output directory:

.. code-block:: python

    from il_supermarket_scarper.scrappers_factory import ScraperFactory

    scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
    scraper = scraper_class(folder_name="my_output")

    # For async usage
    import asyncio
    asyncio.run(scraper.scrape(limit=5))

Consuming Results
~~~~~~~~~~~~~~~~~

To process results as they become available:

.. code-block:: python

    scraper = ScarpingTask()
    scraper.start()

    # Consume results
    for result in scraper.consume():
        print(f"Downloaded: {result.file_name}")
        print(f"Success: {result.extract_succefully}")

    scraper.join()

Docker Usage
------------

Pull the Docker image:

.. code-block:: bash

    docker pull erlichsefi/israeli-supermarket-scarpers:latest

Run with basic configuration:

.. code-block:: bash

    docker run -v "./dumps:/usr/src/app/dumps" \
               -e ENABLED_SCRAPERS="WOLT,YAYNO_BITAN" \
               erlichsefi/israeli-supermarket-scarpers

For more Docker examples, see :ref:`examples`.

Next Steps
----------

* Check out :ref:`examples` for more advanced usage patterns
* Read :ref:`configuration` for detailed configuration options
* Browse the :ref:`api/modules` for complete API reference
