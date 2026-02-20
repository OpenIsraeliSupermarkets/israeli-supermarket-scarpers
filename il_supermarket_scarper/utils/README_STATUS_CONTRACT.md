# Scraper Status Output Contract

This document describes the status output format contract for scrapers.

## Overview

The scraper status output is defined using Pydantic models in `scraper_status_contract.py`. This ensures type safety and automatic validation that the format doesn't drift over time.

## Reference Format

The reference format is defined in `scrappers/tests/t.json`. All status output must conform to this structure.

## Status Event Types

### 1. **started** - Scraping has started
```json
{
    "status": "started",
    "when": "2026-01-05 12:38:40.610760+02:00",
    "limit": 1,
    "files_requested": null,
    "store_id": null,
    "files_names_to_scrape": null,
    "when_date": null,
    "filter_nul": true,
    "filter_zero": true,
    "suppress_exception": true
}
```

### 2. **collected** - File details have been collected from site
```json
{
    "status": "collected",
    "when": "2026-01-05 12:38:43.613704+02:00",
    "file_name_collected_from_site": ["Promo7290875100001-066-202601051222"],
    "links_collected_from_site": ["http://..."]
}
```

### 3. **downloaded** - Files have been downloaded
```json
{
    "status": "downloaded",
    "when": "2026-01-05 12:38:49.688394+02:00",
    "results": [{
        "file_name": "Promo7290875100001-066-202601051222",
        "downloaded": true,
        "extract_succefully": true,
        "error": null,
        "restart_and_retry": false
    }]
}
```

### 4. **fail** - Scraping has failed
```json
{
    "status": "fail",
    "when": "...",
    "execption": "error message",
    "traceback": "...",
    "download_urls": [],
    "file_names": []
}
```

### 5. **estimated_size** - Scraping completed
```json
{
    "status": "estimated_size",
    "when": "2026-01-05 12:38:49.704610+02:00",
    "folder_size": {
        "size": 0.006127357482910156,
        "unit": "MB",
        "folder": "/tmp/...",
        "folder_content": ["/tmp/.../file.xml"]
    },
    "completed_successfully": true
}
```

## Validation

### Automatic Validation in Tests

All tests in `scrappers/tests/test_cases.py` automatically validate status output:

```python
def _make_sure_status_file_is_valid(self, dump_path):
    """Will fail if format has drifted from t.json specification."""
    ScraperStatusOutput.validate_json_file(status_file_path)
```

### Manual Validation

To validate a status JSON file:

```python
from il_supermarket_scarper.utils import ScraperStatusOutput

# This will raise ValidationError if format doesn't match
result = ScraperStatusOutput.validate_json_file('path/to/status.json')
```

## What Happens When Format Drifts?

If the actual output format drifts from the contract:

1. **Pydantic ValidationError** will be raised during validation
2. **Tests will fail** with clear error messages about which fields are missing or incorrect
3. **Type errors** will be caught at validation time, not at runtime

## Updating the Contract

If you need to change the status output format:

1. Update the Pydantic models in `scraper_status_contract.py`
2. Update the reference file `scrappers/tests/t.json`
3. Update `scraper_status.py` to output the new format
4. Run tests to ensure no drift

## Dependencies

- `pydantic==2.10.4` - for model validation (added to `requirements.txt`)

