Israel Supermarket Scraper: Clients to download the data published by the supermarkets.
=======================================
This is a scraper for ALL the supermarket chains listed in the GOV.IL site.

שקיפות מחירים (השוואת מחירים) - https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations




[![Unit & Integration Tests](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/actions/workflows/test-suite.yml/badge.svg?event=push)](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/actions/workflows/test-suite.yml)
[![CodeQL](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/actions/workflows/codeql.yml/badge.svg)](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/actions/workflows/codeql.yml)
[![Pylint](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/actions/workflows/pylint.yml/badge.svg)](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/actions/workflows/pylint.yml)
[![Publish Docker image](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/actions/workflows/docker-publish.yml)
[![Upload Python Package](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/actions/workflows/python-publish.yml/badge.svg)](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/actions/workflows/python-publish.yml)

## 🤗 Want to support my work?
<p align="center">
    <a href="https://buymeacoffee.com/erlichsefi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;">
    </a>
</p>

Daily Automatic Testing
----
The test suite is scheduled to run daily, so you can see if the supermarket chains have changed something in their interface and the package will not work properly.

Status: [![Scheduled Tests](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/actions/workflows/test-suite.yml/badge.svg?event=schedule)](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/actions/workflows/test-suite.yml)

Notice:
- Berekt and Quik are flaky! They will not fail the testing framework, but you can still use them.
- Some of the scrapers sites are blocked from being accessed from outside of Israel. 

--------

 

Got a question?
---------------

You can email me at erlichsefi@gmail.com

If you think you've found a bug:

- Create issue in [issue tracker](https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/issues) to see if
  it's already been reported
- Please consider solving the issue by yourself and creating a pull request.

What is il_supermarket_scarper?
-------------

There are a lot of projects in GitHub trying to scrape the supermarket data, but most of them are not stable or haven't been updated for a while, it's about time there will be one codebase that does the work completely. 

You only need to run the following code to get all the data currently shared by the supermarkets.

```python
from il_supermarket_scarper import ScarpingTask

scraper = ScarpingTask()
scraper.start()
```


Please notice!
Since new files are constantly uploaded by the supermarket to their site, you will only get the current snapshot. In order to keep getting data, you will need to run this code more than one time to get the newly uploaded files.

Quick start
-----------

il_supermarket_scarper can be installed using pip:

    python3 pip install il-supermarket-scraper

If you want to run the latest version of the code, you can install it from the
repo directly:

    python3 -m pip install -U git+https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers.git
    # or if you don't have 'git' installed
    python3 -m pip install -U https://github.com/OpenIsraeliSupermarkets/israeli-supermarket-scarpers/main
    


Running Docker
-----------
The docker is designed to re-run against the same configuration, in every iteration the scraper will collect the files available to download and check if the file already exists before fetching it, either by scanning the dump folder, or checking the mongo/status files.


Build yourself:

    docker build -t erlichsefi/israeli-supermarket-scarpers --target prod .

or pull the existing image from docker hub:

    docker pull erlichsefi/israeli-supermarket-scarpers:latest


Then running it using:


    docker run  -v "./dumps:/usr/src/app/dumps" \
                -e ENABLED_SCRAPERS="BAREKET,YAYNO_BITAN" \   # see: il_supermarket_scarper/scrappers_factory.py
                -e ENABLED_FILE_TYPES="STORE_FILE" \          # see: il_supermarket_scarper/utils/file_types.py
                -e LIMIT=1 \                                  # number of files you would like to download (remove for unlimited)
                -e TODAY="2024-10-23 14:35" \                 # the date to download data from
                -e OUTPUT_MODE="disk" \                       # 'disk' (default) or 'queue' - where to save scraped files
                -e STORAGE_PATH="./dumps" \                   # (optional) custom storage path for disk mode
                erlichsefi/israeli-supermarket-scarpers

For queue output mode:

    docker run  -e OUTPUT_MODE="queue" \
                -e QUEUE_TYPE="memory" \                      # 'memory' (for testing) or 'kafka'
                erlichsefi/israeli-supermarket-scarpers

For Kafka queue output:

    docker run  -e OUTPUT_MODE="queue" \
                -e QUEUE_TYPE="kafka" \
                -e KAFKA_BOOTSTRAP_SERVERS="localhost:9092" \ # Kafka bootstrap servers
                erlichsefi/israeli-supermarket-scarpers


Environment Variables
-----------

The following environment variables can be used to configure the scraper:

### General Configuration
- `ENABLED_SCRAPERS`: Comma-separated list of scrapers to enable (e.g., "BAREKET,YAYNO_BITAN"). See `il_supermarket_scarper/scrappers_factory.py` for all available scrapers.
- `ENABLED_FILE_TYPES`: Comma-separated list of file types to download (e.g., "STORE_FILE,PRICE_FILE"). See `il_supermarket_scarper/utils/file_types.py` for all available types.
- `LIMIT`: Maximum number of files to download (optional, no limit if not specified).
- `NUMBER_OF_PROCESSES`: Number of parallel processes to use (default: 5).
- `TODAY`: Date to download data from, in format "YYYY-MM-DD HH:MM" (e.g., "2024-10-23 14:35").

### Output Configuration
- `OUTPUT_MODE`: Where to save scraped files (default: "disk")
  - `disk`: Save files to local filesystem
  - `queue`: Send files to a message queue

#### Disk Output Mode (default)
- `STORAGE_PATH`: Custom storage path for files (optional, uses default if not specified).

#### Queue Output Mode
- `QUEUE_TYPE`: Type of queue to use (required when OUTPUT_MODE="queue")
  - `memory`: In-memory queue (useful for testing)
  - `kafka`: Apache Kafka message queue


##### Kafka Queue
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka bootstrap servers (default: "localhost:9092").


Contributing
------------

Help in testing, development, documentation and other tasks is
highly appreciated and useful to the project. There are tasks for
contributors of all experience levels.

If you need help getting started, don't hesitate to contact me.


Development status
------------------

IL SuperMarket Scraper is beta software, as far as i see devlopment stoped until new issues will be found.
