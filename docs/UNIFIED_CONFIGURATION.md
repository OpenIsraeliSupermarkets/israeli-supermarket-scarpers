# Unified File Output Configuration

## Overview

The scraper configuration has been **unified** into a single, coherent system that combines:
- **Output location** (`folder_name` for disk or `file_output` for queues)  
- **Scraping options** (filtering, size limits, error handling)
- **Metadata** (custom data to include with files)

This eliminates confusion between multiple configuration approaches and provides a clean, intuitive API.

## Key Concept: One Configuration, Multiple Outputs

```python
# ALL scrapers now accept EITHER:
scraper = ScraperClass(folder_name="output")        # Disk output (simple)
scraper = ScraperClass(file_output=queue_handler)   # Queue output (advanced)

# Or use ScraperConfig for comprehensive settings:
config = ScraperConfig.disk(folder_name="output", filter_null=True, ...)
config = ScraperConfig.queue(file_output=handler, min_size=1000, ...)
```

## The Unified Approach

### Before (Confusing - Two Separate Systems)
```python
# Output location
scraper = SomeClass(folder_name="output")

# File output (separate concept)
file_output = DiskFileOutput("/some/path")
scraper = SomeClass(file_output=file_output)  # Conflicts with folder_name!
```

### After (Unified - One System)
```python
# Simple disk output - just use folder_name
scraper = SomeClass(folder_name="output")
# → Automatically creates DiskFileOutput for that folder

# Queue output - use file_output
scraper = SomeClass(file_output=QueueFileOutput(handler))
# → Uses queue handler directly

# Comprehensive config - use ScraperConfig
config = ScraperConfig.disk(folder_name="output", filter_null=True)
scraper = SomeClass(
    folder_name=config.get_folder_name(),
    file_output=config.get_file_output("ChainName")
)
```

## How It Works

### Priority System

The Engine resolves output configuration in this priority order:

1. **`file_output` parameter** (highest priority)
   - If provided, use it directly
   - Supports queue output, custom handlers, etc.

2. **`folder_name` parameter**
   - If provided (and no file_output), create `DiskFileOutput` for that folder
   - This is the recommended way for disk output

3. **Default**
   - If neither provided, use default output folder for the chain

### Code Flow

```python
# In Engine.__init__:
if file_output is not None:
    # Use provided file output handler
    self.file_output = file_output
else:
    # Create disk output using folder_name (or default)
    storage_path = get_output_folder(chain.value, folder_name=folder_name)
    self.file_output = DiskFileOutput(storage_path, extract_gz=True)
```

## Usage Patterns

### Pattern 1: Simple Disk Output (RECOMMENDED for most cases)

```python
from il_supermarket_scarper.scrappers_factory import ScraperFactory

scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
scraper = scraper_class(folder_name="my_output")

await scraper.scrape(limit=1)
# Files saved to: <base_path>/my_output/Wolt/
```

### Pattern 2: Queue Output

```python
from il_supermarket_scarper.utils import QueueFileOutput, InMemoryQueueHandler

# Create queue handler
queue = InMemoryQueueHandler("test_queue")
output = QueueFileOutput(queue)

# Use queue output
scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
scraper = scraper_class(file_output=output)

await scraper.scrape(limit=1)
# Files sent to queue instead of disk
```

### Pattern 3: Unified Configuration (RECOMMENDED for complex scenarios)

```python
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
```

### Pattern 4: Test Configuration

```python
# In tests, easily switch between disk and queue
import tempfile

# Option A: Test with disk
with tempfile.TemporaryDirectory() as tmpdir:
    scraper = scraper_class(folder_name=tmpdir)
    await scraper.scrape(limit=1)
    # Verify files on disk

# Option B: Test with queue (no disk I/O)
queue = InMemoryQueueHandler("test")
scraper = scraper_class(file_output=QueueFileOutput(queue))
await scraper.scrape(limit=1)
messages = queue.get_all_messages()
# Verify messages
```

## ScraperConfig API

### Class Methods

```python
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
```

### Instance Methods

```python
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
```

### Configuration Properties

```python
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
```

## Migration Guide

### From Old Code

```python
# OLD: Just folder_name
scraper = SomeClass(folder_name="output")
```

```python
# NEW: Same! (100% compatible)
scraper = SomeClass(folder_name="output")
```

### Adding Queue Support

```python
# OLD: Only disk output
scraper = SomeClass(folder_name="output")
await scraper.scrape(limit=1)
```

```python
# NEW: Add queue output option
if use_queue:
    queue = InMemoryQueueHandler("queue")
    scraper = SomeClass(file_output=QueueFileOutput(queue))
else:
    scraper = SomeClass(folder_name="output")
await scraper.scrape(limit=1)
```

### Using ScraperConfig

```python
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
```

```python
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
```

## Benefits of Unified Configuration

1. **Single Source of Truth**: All configuration in one place
2. **No Conflicts**: `folder_name` and `file_output` work together seamlessly
3. **Type Safety**: Clear distinction between disk and queue output
4. **Easy Testing**: Switch between disk and queue without changing much code
5. **Backward Compatible**: Existing code works without changes
6. **Extensible**: Easy to add new configuration options

## Test Examples

```python
import pytest
from il_supermarket_scarper.utils import ScraperConfig, InMemoryQueueHandler, QueueFileOutput

def test_with_disk():
    """Test with disk output"""
    config = ScraperConfig.disk(folder_name="test_output")
    scraper = create_scraper(
        folder_name=config.get_folder_name(),
        file_output=config.get_file_output("TestChain")
    )
    # Test...

def test_with_queue():
    """Test with queue output (no disk I/O)"""
    queue = InMemoryQueueHandler("test")
    config = ScraperConfig.queue(file_output=QueueFileOutput(queue))
    scraper = create_scraper(
        file_output=config.get_file_output("TestChain")
    )
    # Test...
    messages = queue.get_all_messages()
    assert len(messages) > 0
```

## Complete Example

```python
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import ScraperConfig, InMemoryQueueHandler, QueueFileOutput

# Define configuration based on environment
if environment == "production":
    config = ScraperConfig.disk(
        folder_name="/data/supermarket/output",
        filter_null=True,
        filter_zero=True,
        min_size=1000,
        max_size=10_000_000,
        metadata={"env": "prod", "version": "1.0"}
    )
elif environment == "streaming":
    kafka_handler = KafkaQueueHandler("localhost:9092", "files")
    config = ScraperConfig.queue(
        file_output=QueueFileOutput(kafka_handler),
        filter_null=True,
        min_size=1000,
        metadata={"env": "streaming"}
    )
else:  # test
    queue = InMemoryQueueHandler("test")
    config = ScraperConfig.queue(
        file_output=QueueFileOutput(queue),
        filter_null=False,  # Allow all files in test
        metadata={"env": "test"}
    )

# Create scraper with unified config
scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
scraper = scraper_class(
    folder_name=config.get_folder_name(),
    file_output=config.get_file_output("Wolt")
)

# Scrape with config settings
await scraper.scrape(
    limit=10,
    filter_null=config.filter_null,
    filter_zero=config.filter_zero,
    min_size=config.min_size,
    max_size=config.max_size,
    suppress_exception=config.suppress_exception
)

print(f"Output: {scraper.file_output.get_output_location()}")
print(f"Type: {'Disk' if config.is_disk_output() else 'Queue'}")
```

## Summary

The **unified configuration** system provides:
- ✅ Single, coherent API for all output options
- ✅ No conflicts between `folder_name` and `file_output`
- ✅ 100% backward compatible with existing code
- ✅ Easy to extend with new output types
- ✅ Clean separation between disk and queue output
- ✅ Comprehensive configuration management via `ScraperConfig`

**Recommendation**: Use `folder_name` for simple disk output, `ScraperConfig` for complex scenarios with multiple options.

