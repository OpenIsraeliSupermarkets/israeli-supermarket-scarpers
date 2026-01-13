from il_supermarket_scarper import ScarpingTask, ScraperFactory
from il_supermarket_scarper.utils import _now, Logger, QueueFileOutput

Logger.set_logging_level("INFO")

if __name__ == "__main__":
    # Configure for in-memory queue output
    # When using multiprocessing, the queue automatically uses shared memory
    scraper = ScarpingTask(
        output_configuration={
            "output_mode": "queue",
            "queue_type": "memory",  # Automatically shares across processes
        },
        status_configuration={"database_type": "json", "base_path": "status_logs"},
        multiprocessing=1,
        enabled_scrapers=[ScraperFactory.BAREKET.name, ScraperFactory.VICTORY.name],
    )
    
    # Start scraping (runs in background thread)
    scraper.start(limit=1, when_date=_now())
    
    # Wait for scraping to complete
    scraper._thread.join()
    
    # Get file outputs from the runner
    file_outputs = scraper.consume()
    
    # Access files from the in-memory queue
    for scraper_name, file_output in file_outputs.items():
        if isinstance(file_output, QueueFileOutput):
            
            # Get all messages from the queue
            messages = file_output.queue_handler.get_all_messages()
            
            print(f"\n=== Files from {scraper_name} ===")
            print(f"Total files in queue: {len(messages)}")
            
            # Read each file from the queue
            for i, msg in enumerate(messages, 1):
                file_name = msg["file_name"]
                file_content = msg["file_content"]  # bytes
                file_link = msg["file_link"]
                metadata = msg["metadata"]
                
                print(f"\nFile {i}: {file_name}")
                print(f"  Link: {file_link}")
                print(f"  Size: {len(file_content)} bytes")
                print(f"  Metadata: {metadata}")
                
                # Read file content (example: decode if XML/text)
                if file_name.endswith(".xml"):
                    try:
                        content_str = file_content.decode("utf-8")
                        print(f"  Content preview (first 200 chars):")
                        print(f"  {content_str[:200]}...")
                    except UnicodeDecodeError:
                        print(f"  Content: binary data")
                else:
                    print(f"  Content: binary data ({len(file_content)} bytes)")
    
    # Stop and cleanup
    scraper.stop()