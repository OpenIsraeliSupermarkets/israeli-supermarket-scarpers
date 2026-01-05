"""
Example usage of the file output configuration system.

This demonstrates the UNIFIED configuration approach where folder_name and file_output
are integrated into a single system.
"""

import asyncio
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import (
    DiskFileOutput,
    QueueFileOutput,
    InMemoryQueueHandler,
    KafkaQueueHandler,
    ScraperConfig,
)


async def example_disk_output():
    """Example 1: Save files to disk using folder_name (simplest)"""
    print("\n=== Example 1: Disk Output (folder_name) ===")

    # RECOMMENDED: Use folder_name for disk output
    scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
    scraper = scraper_class(folder_name="output_example")

    # Automatically creates DiskFileOutput for that folder
    print(f"Output location: {scraper.file_output.get_output_location()}")
    print(f"Storage path: {scraper.storage_path}")


async def example_custom_disk_output():
    """Example 2: Save files to disk with custom configuration"""
    print("\n=== Example 2: Custom Disk Output ===")

    # Create custom disk output (e.g., without extraction)
    custom_output = DiskFileOutput(
        storage_path="/tmp/custom_scraper_output", extract_gz=False
    )

    # Create scraper with custom output
    scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
    scraper = scraper_class(folder_name="output_example", file_output=custom_output)

    print(f"Output location: {scraper.file_output.get_output_location()}")


async def example_inmemory_queue():
    """Example 3: Send files to in-memory queue (for testing)"""
    print("\n=== Example 3: In-Memory Queue ===")

    # Create in-memory queue handler
    queue_handler = InMemoryQueueHandler(queue_name="test_queue")

    # Create queue output
    queue_output = QueueFileOutput(queue_handler)

    # Create scraper with queue output
    scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
    scraper = scraper_class(folder_name="output_example", file_output=queue_output)

    print(f"Output location: {scraper.file_output.get_output_location()}")

    # After scraping, you can access the messages
    # messages = queue_handler.get_all_messages()
    # print(f"Collected {len(messages)} files in queue")


async def example_kafka_queue():
    """Example 4: Send files to Kafka"""
    print("\n=== Example 4: Kafka Queue ===")

    try:
        # Create Kafka queue handler
        # Note: Requires aiokafka to be installed
        kafka_handler = KafkaQueueHandler(
            bootstrap_servers="localhost:9092", topic="supermarket_files"
        )

        # Create queue output
        queue_output = QueueFileOutput(kafka_handler)

        # Create scraper with Kafka output
        scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
        scraper = scraper_class(folder_name="output_example", file_output=queue_output)

        print(f"Output location: {scraper.file_output.get_output_location()}")

        # Don't forget to close the Kafka connection when done
        # await kafka_handler.close()

    except ImportError as e:
        print(f"Kafka example skipped: {e}")


async def example_with_scraper_config():
    """Example 5: Using ScraperConfig for comprehensive configuration"""
    print("\n=== Example 5: ScraperConfig (RECOMMENDED) ===")

    # Create unified configuration - choose disk OR queue

    # Option A: Disk output config
    disk_config = ScraperConfig.disk(
        folder_name="my_custom_output",
        filter_null=True,
        filter_zero=True,
        min_size=1000,
        max_size=5_000_000,
        metadata={"environment": "production"},
    )

    # Option B: Queue output config
    queue_handler = InMemoryQueueHandler(queue_name="configured_queue")
    queue_config = ScraperConfig.queue(
        file_output=QueueFileOutput(queue_handler),
        filter_null=True,
        filter_zero=True,
        min_size=1000,
        max_size=5_000_000,
        metadata={"environment": "test", "version": "1.0"},
    )

    # Use the config (let's use queue_config for this example)
    config = queue_config

    # Create scraper with unified config
    scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
    file_output = config.get_file_output("Wolt", default_folder="output_example")
    scraper = scraper_class(
        folder_name=config.get_folder_name() or "output_example",
        file_output=file_output,
    )

    # Use config values in scraping call
    # await scraper.scrape(
    #     limit=1,
    #     filter_null=config.filter_null,
    #     filter_zero=config.filter_zero,
    #     min_size=config.min_size,
    #     max_size=config.max_size,
    #     suppress_exception=config.suppress_exception,
    # )

    print(f"Output location: {scraper.file_output.get_output_location()}")
    print(f"Is disk output: {config.is_disk_output()}")
    print(f"Is queue output: {config.is_queue_output()}")
    print(f"Filter config: null={config.filter_null}, zero={config.filter_zero}")
    print(f"Size limits: {config.min_size}-{config.max_size} bytes")


async def main():
    """Run all examples"""
    await example_disk_output()
    await example_custom_disk_output()
    await example_inmemory_queue()
    await example_kafka_queue()
    await example_with_scraper_config()


if __name__ == "__main__":
    asyncio.run(main())
