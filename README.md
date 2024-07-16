Israel Supermarket Scraper: Clients to download the data published by the supermarkets.
=======================================
This is a scraper for ALL the supermarket chains listed in the GOV.IL site.

שקיפות מחירים (השוואת מחירים) - https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations




[![Unit & Integration Tests](https://github.com/erlichsefi/israeli-supermarket-scarpers/actions/workflows/test-suite.yml/badge.svg?event=push)](https://github.com/erlichsefi/israeli-supermarket-scarpers/actions/workflows/test-suite.yml)
[![CodeQL](https://github.com/erlichsefi/israeli-supermarket-scarpers/actions/workflows/codeql.yml/badge.svg)](https://github.com/erlichsefi/israeli-supermarket-scarpers/actions/workflows/codeql.yml)
[![Pylint](https://github.com/erlichsefi/israeli-supermarket-scarpers/actions/workflows/pylint.yml/badge.svg)](https://github.com/erlichsefi/israeli-supermarket-scarpers/actions/workflows/pylint.yml)
[![Publish Docker image](https://github.com/erlichsefi/israeli-supermarket-scarpers/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/erlichsefi/israeli-supermarket-scarpers/actions/workflows/docker-publish.yml)
[![Upload Python Package](https://github.com/erlichsefi/israeli-supermarket-scarpers/actions/workflows/python-publish.yml/badge.svg)](https://github.com/erlichsefi/israeli-supermarket-scarpers/actions/workflows/python-publish.yml)

## 🤗 Want to support my work?
<p align="center">
    <a href="https://buymeacoffee.com/erlichsefi" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;">
    </a>
</p>

Scheduled Automatic Testing
----
The test-suite is scheduled to run every three days, so you can see if the supermarket chains has chanced something in their interface and the package will not work probably.

Status: [![Scheduled Tests](https://github.com/erlichsefi/israeli-supermarket-scarpers/actions/workflows/test-suite.yml/badge.svg?event=schedule)](https://github.com/erlichsefi/israeli-supermarket-scarpers/actions/workflows/test-suite.yml)

Notice:
- Berekt and Quik are flaky! They will not fail the testing framework, but you can still use them.
- Some of the scrapers site are blocked to be accessed from outside of israel. 

--------

 

Got a question?
---------------

You can email me at erlichsefi@gmail.com

If you think you've found a bug:

- Create issue in [issue tracker](https://github.com/erlichsefi/israeli-supermarket-scarpers/issues) to see if
  it's already been reported
- Please consider solving the issue by yourself and creating a pull request.

What is il_supermarket_scarper?
-------------

There are alot of projects in github trying to scrape the supermarket data, most of them are not stable or wasn't updated for a while, it's about time there will be one codebase that does the work completely. 

You only need to run the following code to get all the data currently shared by the supermarkets.

```python
from il_supermarket_scarper import MainScrapperRunner

scraper = MainScrapperRunner()
scraper.run()
```


Please notice!
Since new files are constantly uploaded by the supermarket to their site, you will only get the current snapshot. In order to keep geting data, you will need to run this code more the one time to get the newly uploaded files.

Quick start
-----------

il_supermarket_scarper can be installed using pip:

    python3 pip install il-supermarket-scraper

If you want to run the latest version of the code, you can install from the
repo directly:

    python3 -m pip install -U git+https://github.com/erlichsefi/israeli-supermarket-scarpers.git
    # or if you don't have 'git' installed
    python3 -m pip install -U https://github.com/erlichsefi/israeli-supermarket-scarpers/master
    


Running Docker
-----------
The docker is designed to run the scaper every 6 hours, (you change the cron expression if you would like, checkout the file 'crontab'), in every itreation the scraper will collect the files avaliabe to download and check if the file alreay exists before fetching it, either by scaning the dump folder, or checking the mongo.


    docker-compose up -d

or if you want to use the existing image from docker hub:

    docker pull erlichsefi/israeli-supermarket-scarpers:latest

Contributing
------------

Help in testing, development, documentation and other tasks is
highly appreciated and useful to the project. There are tasks for
contributors of all experience levels.

If you need help getting started, don't hesitate to contact me.


Development status
------------------

IL SuperMarket Scraper is beta software, as far as i see devlopment stoped until new issues will be found.
