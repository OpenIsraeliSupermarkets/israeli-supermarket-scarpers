Israel Supermarket Scraper: Clients to download the data published by the supermarkets.
=======================================
שקיפות מחירים (השוואת מחירים)


https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations

Got a question?
---------------

You can email me at erlichsefi@gmail.com

If you think you've found a bug:

- Create issue in [issue tracker](https://github.com/erlichsefi/il_supermarket_scarper/issues) to see if
  it's already been reported
- consider asking offering creating a pull request.

What is il_supermarket_scarper?
-------------

There are alot of projects in github tring to scrape the supermarket data, must of them are not stable or wasn't updated of a while, it's about time there will be one codebase the those the work completely. 

You only need to run the following code to get all the data currently shared by the supermarkets, please notice that since new files are constantly uploaded by the supermarket, you will need to run this code more the one time to get the newly uploaded files. 

```python
from il_supermarket_scarper import MainScrapperRunner

scraper = MainScrapperRunner()
scraper.run()

```

Quick start
-----------

Mypy can be installed using pip:

    python3 -m pip install -U il_supermarket_scarper

If you want to run the latest version of the code, you can install from the
repo directly:

    python3 -m pip install -U git+https://github.com/erlichsefi/il_supermarket_scarper.git
    # or if you don't have 'git' installed
    python3 -m pip install -U https://github.com/erlichsefi/il_supermarket_scarper/master


Contributing
------------

Help in testing, development, documentation and other tasks is
highly appreciated and useful to the project. There are tasks for
contributors of all experience levels.

To get started with developing mypy, see [CONTRIBUTING.md](CONTRIBUTING.md).

If you need help getting started, don't hesitate to ask contact me.


Development status
------------------

IL SuperMarket Scraper is beta software, as far as i see devlopment stoped until new issues will be found.
