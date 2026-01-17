from il_supermarket_scarper import ScarpingTask, ScraperFactory
from il_supermarket_scarper.utils import _now, Logger, QueueFileOutput
import asyncio
Logger.set_logging_level("INFO")

async def main():
    scraper = ScarpingTask(
        output_configuration={
            "output_mode": "queue",
            "queue_type": "memory",
        },
        status_configuration={"database_type": "json", "base_path": "status_logs"},
        multiprocessing=1,
        enabled_scrapers=[ScraperFactory.BAREKET.name, ScraperFactory.VICTORY.name],
    )

    # Start scraping (runs in background thread)
    scraper.start(limit=1, when_date=_now())

    # Consume messages AS THEY ARRIVE while scraping runs
    # All scrapers share queues, so we need to track which are done
    async def consume_queue(consumed_count: int = 0):
        """Consume messages from a single queue."""
        for name, file_output in scraper.consume().items():
            count = 0
            async for msg in file_output.queue_handler.get_all_messages():
                count += 1
                file_name = msg["file_name"]
                file_content = msg["file_content"]
                file_link = msg["file_link"]
                metadata = msg["metadata"]

                print(f"\n[{name}] File: {file_name}")
                print(f"  Link: {file_link}")
                print(f"  Size: {len(file_content)} bytes")
                print(f"  Metadata: {metadata}")

                if file_name.endswith(".xml"):
                    try:
                        content_str = file_content.decode("utf-8")
                        print(f"  Content preview: {content_str[:200]}...")
                    except UnicodeDecodeError:
                        print(f"  Content: binary data")
                else:
                    print(f"  Content: binary data")

                if consumed_count == count:
                    break

    await consume_queue(consumed_count=1)


    scraper.stop()
    scraper.join()

    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(main())