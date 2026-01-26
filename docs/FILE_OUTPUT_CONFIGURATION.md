# File Output Configuration

This document describes how to configure where and how scraped files are saved using the flexible file output system.

## Overview

The Israeli Supermarket Scrapers now support two output modes:
1. **Disk Output** (default) - Save files to local filesystem
2. **Queue Output** - Send files to external queues (Kafka, RabbitMQ, etc.)

This allows you to integrate scraped data into streaming pipelines, message queues, or other downstream systems.

## Quick Start

### Option 1: Default Disk Output (No Changes Required)

```python
from il_supermarket_scarper.scrappers_factory import ScraperFactory

# Create scraper - saves to disk by default
scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
scraper = scraper_class(folder_name="my_output")

await scraper.scrape(limit=1)
```

### Option 2: Custom Disk Output

```python
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import DiskFileOutput

# Create custom disk output
custom_output = DiskFileOutput(
    storage_path="/custom/path",
    extract_gz=False  # Keep .gz files compressed
)

scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
scraper = scraper_class(
    folder_name="my_output",
    file_output=custom_output
)

await scraper.scrape(limit=1)
```

### Option 3: In-Memory Queue (for Testing)

```python
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import (
    QueueFileOutput,
    InMemoryQueueHandler
)

# Create queue handler
queue_handler = InMemoryQueueHandler(queue_name="test_queue")
queue_output = QueueFileOutput(queue_handler)

# Create scraper with queue output
scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
scraper = scraper_class(
    folder_name="my_output",
    file_output=queue_output
)

await scraper.scrape(limit=1)

# Access collected messages
messages = queue_handler.get_all_messages()
for msg in messages:
    print(f"File: {msg['file_name']}, Size: {len(msg['file_content'])} bytes")
```

### Option 4: Kafka Queue

```python
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import (
    QueueFileOutput,
    KafkaQueueHandler
)

# Create Kafka handler (requires aiokafka: pip install aiokafka)
kafka_handler = KafkaQueueHandler(
    bootstrap_servers="localhost:9092",
    topic="supermarket_files"
)
queue_output = QueueFileOutput(kafka_handler)

# Create scraper with Kafka output
scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
scraper = scraper_class(
    folder_name="my_output",
    file_output=queue_output
)

await scraper.scrape(limit=1)

# Clean up
await kafka_handler.close()
```

## Architecture

### FileOutput Interface

All file output handlers implement the `FileOutput` abstract base class:

```python
class FileOutput(ABC):
    @abstractmethod
    async def save_file(
        self,
        file_link: str,
        file_name: str,
        file_content: bytes,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Save a file and return status information."""
        pass

    @abstractmethod
    def get_output_location(self) -> str:
        """Get a string representation of where files are being saved."""
        pass
```

### Built-in Implementations

1. **DiskFileOutput** - Saves files to local filesystem
   - Supports automatic .gz extraction
   - Creates directories as needed
   - Same behavior as previous versions

2. **QueueFileOutput** - Sends files to message queues
   - Requires an `AbstractQueueHandler` implementation
   - Sends file content and metadata as messages

### Queue Handlers

Queue handlers implement the `AbstractQueueHandler` interface:

```python
class AbstractQueueHandler(ABC):
    @abstractmethod
    async def send(self, message: Dict[str, Any]) -> None:
        """Send a message to the queue."""
        pass

    @abstractmethod
    def get_queue_name(self) -> str:
        """Return the name/identifier of the queue."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the queue connection."""
        pass
```

### Built-in Queue Handlers

1. **InMemoryQueueHandler** - Simple in-memory queue for testing
   - Not persistent
   - Provides `get_all_messages()` for testing

2. **KafkaQueueHandler** - Kafka integration
   - Requires `aiokafka` package
   - Sends messages to Kafka topic

## Creating Custom Handlers

### Custom Disk Handler Example

```python
from il_supermarket_scarper.utils import FileOutput
import boto3
import asyncio

class S3FileOutput(FileOutput):
    """Save files to AWS S3."""

    def __init__(self, bucket_name: str, prefix: str = ""):
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.s3_client = boto3.client('s3')

    async def save_file(self, file_link, file_name, file_content, metadata=None):
        try:
            key = f"{self.prefix}/{file_name}" if self.prefix else file_name

            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                Metadata=metadata or {}
            )

            return {
                "file_name": file_name,
                "saved": True,
                "extract_successfully": True,
                "error": None,
                "metadata": metadata or {}
            }
        except Exception as e:
            return {
                "file_name": file_name,
                "saved": False,
                "extract_successfully": False,
                "error": str(e),
                "metadata": metadata or {}
            }

    def get_output_location(self) -> str:
        return f"s3://{self.bucket_name}/{self.prefix}"
```

### Custom Queue Handler Example

```python
from il_supermarket_scarper.utils import AbstractQueueHandler
import pika
import json

class RabbitMQHandler(AbstractQueueHandler):
    """RabbitMQ queue handler."""

    def __init__(self, host: str, queue_name: str):
        self.host = host
        self.queue_name = queue_name
        self.connection = None
        self.channel = None

    async def send(self, message):
        if self.connection is None:
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=self.host)
            )
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.queue_name, durable=True)

        # Send metadata only (file content might be too large)
        payload = {
            "file_name": message["file_name"],
            "file_link": message["file_link"],
            "file_size": len(message["file_content"]),
            "metadata": message["metadata"]
        }

        self.channel.basic_publish(
            exchange='',
            routing_key=self.queue_name,
            body=json.dumps(payload),
            properties=pika.BasicProperties(delivery_mode=2)
        )

    def get_queue_name(self) -> str:
        return f"rabbitmq://{self.host}/{self.queue_name}"

    async def close(self) -> None:
        if self.connection:
            self.connection.close()
```

## Using with ScraperConfig

For comprehensive configuration, use `ScraperConfig`:

```python
from il_supermarket_scarper.utils import (
    ScraperConfig,
    QueueFileOutput,
    InMemoryQueueHandler
)

# Create configuration
queue_handler = InMemoryQueueHandler(queue_name="my_queue")
config = ScraperConfig(
    file_output=QueueFileOutput(queue_handler),
    filter_null=True,
    filter_zero=True,
    min_size=1000,  # 1 KB minimum
    max_size=5_000_000,  # 5 MB maximum
    suppress_exception=False,
    metadata={"environment": "production", "version": "2.0"}
)

# Use with scraper
scraper = scraper_class(
    folder_name="output",
    file_output=config.file_output
)

await scraper.scrape(
    limit=10,
    filter_null=config.filter_null,
    filter_zero=config.filter_zero,
    min_size=config.min_size,
    max_size=config.max_size,
    suppress_exception=config.suppress_exception
)
```

## Testing with File Output

In tests, you can verify file output behavior:

```python
import pytest
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import (
    QueueFileOutput,
    InMemoryQueueHandler
)

@pytest.mark.asyncio
async def test_scraper_with_queue():
    # Create queue handler
    queue_handler = InMemoryQueueHandler("test")
    queue_output = QueueFileOutput(queue_handler)

    # Create scraper
    scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
    scraper = scraper_class(
        folder_name="test_output",
        file_output=queue_output
    )

    # Scrape
    await scraper.scrape(limit=1)

    # Verify messages were sent to queue
    messages = queue_handler.get_all_messages()
    assert len(messages) > 0
    assert "file_content" in messages[0]
    assert "metadata" in messages[0]
```

## Migration Guide

### For existing code

No changes required! The system defaults to disk output, maintaining backward compatibility.

### To add queue support

1. Install queue library (e.g., `pip install aiokafka` for Kafka)
2. Create queue handler
3. Pass file_output parameter to scraper initialization
4. That's it!

### For library maintainers

If you're creating a subclass of `Engine`, the `file_output` parameter is automatically available through the parent constructor:

```python
class MyCustomEngine(Engine):
    def __init__(self, chain, chain_id,  file_output=None):
        super().__init__(
            chain,
            chain_id,
            
            file_output=file_output  # Passed through
        )
```

## Best Practices

1. **For Production**: Use proper queue handlers (Kafka, RabbitMQ) with retry logic
2. **For Testing**: Use `InMemoryQueueHandler` to avoid file I/O overhead
3. **Large Files**: Consider uploading to S3/GCS first, then sending URLs via queue
4. **Error Handling**: Always check the `error` field in returned dictionaries
5. **Resource Cleanup**: Call `await queue_handler.close()` when done

## Troubleshooting

### Kafka Connection Errors

```
ImportError: aiokafka is not installed
```

**Solution**: `pip install aiokafka`

### Queue Messages Too Large

If sending full file content causes issues:
1. Upload files to S3/GCS
2. Send only URLs and metadata via queue

### Memory Issues with InMemoryQueue

`InMemoryQueueHandler` stores all messages in RAM. For large-scale testing, use a real queue or disk output.

## See Also

- [examples/file_output_configuration.py](../examples/file_output_configuration.py) - Complete examples
- [il_supermarket_scarper/utils/file_output.py](../il_supermarket_scarper/utils/file_output.py) - Implementation
- [il_supermarket_scarper/utils/scraper_config.py](../il_supermarket_scarper/utils/scraper_config.py) - Configuration

