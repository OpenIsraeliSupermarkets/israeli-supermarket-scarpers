Configuration
=============

This guide covers all configuration options for the Israeli Supermarket Scraper.

Unified Configuration System
----------------------------

The scraper uses a unified configuration system that combines:

* **Output location** (``folder_name`` for disk or ``file_output`` for queues)
* **Scraping options** (filtering, size limits, error handling)
* **Metadata** (custom data to include with files)

This provides a clean, intuitive API without conflicts between different configuration approaches.

Key Concept: One Configuration, Multiple Outputs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All scrapers accept either:

.. code-block:: python

    # Disk output (simple)
    scraper = ScraperClass(folder_name="output")

    # Queue output (advanced)
    scraper = ScraperClass(file_output=queue_handler)

    # Or use ScraperConfig for comprehensive settings
    config = ScraperConfig.disk(folder_name="output", filter_null=True, ...)
    config = ScraperConfig.queue(file_output=handler, min_size=1000, ...)

Priority System
~~~~~~~~~~~~~~~

The Engine resolves output configuration in this priority order:

1. **``file_output`` parameter** (highest priority)
   - If provided, use it directly
   - Supports queue output, custom handlers, etc.

2. **``folder_name`` parameter**
   - If provided (and no file_output), create ``DiskFileOutput`` for that folder
   - This is the recommended way for disk output

3. **Default**
   - If neither provided, use default output folder for the chain

Usage Patterns
--------------

Pattern 1: Simple Disk Output (Recommended for most cases)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from il_supermarket_scarper.scrappers_factory import ScraperFactory

    scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
    scraper = scraper_class(folder_name="my_output")

    await scraper.scrape(limit=1)
    # Files saved to: <base_path>/my_output/Wolt/

Pattern 2: Queue Output
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from il_supermarket_scarper.utils import QueueFileOutput, InMemoryQueueHandler

    # Create queue handler
    queue = InMemoryQueueHandler("test_queue")
    output = QueueFileOutput(queue)

    # Use queue output
    scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
    scraper = scraper_class(file_output=output)

    await scraper.scrape(limit=1)
    # Files sent to queue instead of disk

Pattern 3: Unified Configuration (Recommended for complex scenarios)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from il_supermarket_scarper.utils import ScraperConfig

    # Create unified config
    config = ScraperConfig.disk(
        folder_name="production_output",
        filter_null=True,
        filter_zero=True,
        min_size=1000,
        max_size=5_000_000,
        suppress_exception=False,
        metadata={"environment": "prod", "version": "2.0"}
    )

    # Use with scraper
    scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
    scraper = scraper_class(
        folder_name=config.get_folder_name(),
        file_output=config.get_file_output("Wolt")
    )

    # Apply config to scraping
    await scraper.scrape(
        limit=10,
        filter_null=config.filter_null,
        filter_zero=config.filter_zero,
        min_size=config.min_size,
        max_size=config.max_size,
        suppress_exception=config.suppress_exception
    )

ScraperConfig API
-----------------

Class Methods
~~~~~~~~~~~~~

.. code-block:: python

    # Create disk output config
    config = ScraperConfig.disk(
        folder_name="output",
        filter_null=True,
        ...
    )

    # Create queue output config
    config = ScraperConfig.queue(
        file_output=QueueFileOutput(handler),
        filter_null=True,
        ...
    )

Instance Methods
~~~~~~~~~~~~~~~~

.. code-block:: python

    # Get folder name for status files
    folder = config.get_folder_name()  # Returns folder_name or None

    # Get file output handler (creates if needed)
    output = config.get_file_output(
        chain_name="Wolt",
        default_folder="fallback"
    )

    # Check output type
    is_disk = config.is_disk_output()    # True if disk
    is_queue = config.is_queue_output()  # True if queue

Configuration Properties
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    config = ScraperConfig(
        # Output (choose ONE)
        folder_name="output",        # For disk output
        file_output=handler,         # For queue output

        # Filtering
        filter_null=True,            # Filter NULL files
        filter_zero=True,            # Filter zero files
        min_size=100,                # Minimum file size (bytes)
        max_size=10_000_000,         # Maximum file size (bytes)

        # Behavior
        suppress_exception=False,    # Raise or suppress errors

        # Metadata
        metadata={"key": "value"}    # Custom metadata
    )

File Output Options
-------------------

Disk Output
~~~~~~~~~~~

Save files to local filesystem:

.. code-block:: python

    from il_supermarket_scarper.utils import DiskFileOutput

    # Simple disk output
    scraper = scraper_class(folder_name="output")

    # Custom disk output
    custom_output = DiskFileOutput(
        storage_path="/custom/path",
        extract_gz=False  # Keep .gz files compressed
    )
    scraper = scraper_class(file_output=custom_output)

Queue Output
~~~~~~~~~~~~

Send files to message queues:

.. code-block:: python

    from il_supermarket_scarper.utils import (
        QueueFileOutput,
        InMemoryQueueHandler,
        KafkaQueueHandler
    )

    # In-memory queue (for testing)
    queue = InMemoryQueueHandler("test_queue")
    output = QueueFileOutput(queue)

    # Kafka queue (requires aiokafka)
    kafka_handler = KafkaQueueHandler(
        bootstrap_servers="localhost:9092",
        topic="supermarket_files"
    )
    output = QueueFileOutput(kafka_handler)

Status Database Configuration
-----------------------------

Configure where status information is stored:

.. code-block:: python

    from il_supermarket_scarper.utils.databases import JsonStatusDatabase

    # JSON-based status database
    status_db = JsonStatusDatabase(
        base_path="dumps/status",
        chain_name="Wolt"
    )

    scraper = scraper_class(
        folder_name="output",
        status_database=status_db
    )

Environment Variables
---------------------

The scraper can be configured via environment variables, especially useful for Docker:

General Configuration
~~~~~~~~~~~~~~~~~~~~~

* ``ENABLED_SCRAPERS``: Comma-separated list of scrapers to enable (e.g., "WOLT,YAYNO_BITAN")
* ``ENABLED_FILE_TYPES``: Comma-separated list of file types (e.g., "STORE_FILE,PRICE_FILE")
* ``LIMIT``: Maximum number of files to download
* ``NUMBER_OF_PROCESSES``: Number of parallel processes (default: 5)
* ``TODAY``: Date to download data from, format "YYYY-MM-DD HH:MM"

Output Configuration
~~~~~~~~~~~~~~~~~~~~

* ``OUTPUT_MODE``: Where to save files
  - ``disk``: Save to local filesystem (default)
  - ``queue``: Send to message queue

Disk Output Mode
~~~~~~~~~~~~~~~~

* ``STORAGE_PATH``: Custom storage path for files

Queue Output Mode
~~~~~~~~~~~~~~~~~

* ``QUEUE_TYPE``: Type of queue to use
  - ``memory``: In-memory queue (for testing)
  - ``kafka``: Apache Kafka message queue

Kafka Queue
~~~~~~~~~~~

* ``KAFKA_BOOTSTRAP_SERVERS``: Kafka bootstrap servers (default: "localhost:9092")

Migration Guide
---------------

From Old Code
~~~~~~~~~~~~~

Existing code continues to work without changes:

.. code-block:: python

    # OLD: Just folder_name
    scraper = SomeClass(folder_name="output")

    # NEW: Same! (100% compatible)
    scraper = SomeClass(folder_name="output")

Adding Queue Support
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # OLD: Only disk output
    scraper = SomeClass(folder_name="output")
    await scraper.scrape(limit=1)

    # NEW: Add queue output option
    if use_queue:
        queue = InMemoryQueueHandler("queue")
        scraper = SomeClass(file_output=QueueFileOutput(queue))
    else:
        scraper = SomeClass(folder_name="output")
    await scraper.scrape(limit=1)

Using ScraperConfig
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # OLD: Parameters scattered
    scraper = SomeClass(folder_name="output")
    await scraper.scrape(
        limit=10,
        filter_null=True,
        filter_zero=True,
        min_size=1000,
        max_size=5_000_000,
        suppress_exception=False
    )

    # NEW: Unified config
    config = ScraperConfig.disk(
        folder_name="output",
        filter_null=True,
        filter_zero=True,
        min_size=1000,
        max_size=5_000_000,
        suppress_exception=False
    )

    scraper = SomeClass(
        folder_name=config.get_folder_name(),
        file_output=config.get_file_output("ChainName")
    )

    await scraper.scrape(
        limit=10,
        filter_null=config.filter_null,
        filter_zero=config.filter_zero,
        min_size=config.min_size,
        max_size=config.max_size,
        suppress_exception=config.suppress_exception
    )

Benefits of Unified Configuration
---------------------------------

1. **Single Source of Truth**: All configuration in one place
2. **No Conflicts**: ``folder_name`` and ``file_output`` work together seamlessly
3. **Type Safety**: Clear distinction between disk and queue output
4. **Easy Testing**: Switch between disk and queue without changing much code
5. **Backward Compatible**: Existing code works without changes
6. **Extensible**: Easy to add new configuration options

Recommendation
~~~~~~~~~~~~~~

* Use ``folder_name`` for simple disk output
* Use ``ScraperConfig`` for complex scenarios with multiple options

For more examples, see :ref:`examples`.
