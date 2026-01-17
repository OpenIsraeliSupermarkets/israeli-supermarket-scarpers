.. il-supermarket-scraper documentation master file

Welcome to il-supermarket-scraper's documentation!
==================================================

This is a Python package that implements scraping for Israeli supermarket data.
The scraper supports all supermarket chains listed on the GOV.IL site.

**שקיפות מחירים (השוואת מחירים)** - https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations

Overview
--------

The ``il-supermarket-scraper`` package provides a comprehensive solution for downloading
price and store data published by Israeli supermarkets. It supports all supermarket chains
listed on the GOV.IL site and provides flexible configuration options for output handling,
filtering, and processing.

Key Features:

* Support for all Israeli supermarket chains
* Flexible output options (disk or queue-based)
* Configurable file filtering and size limits
* Status tracking and database integration
* Docker support for easy deployment
* Thread-safe and async-capable

.. toctree::
   :maxdepth: 2
   :caption: Documentation:

   getting_started
   examples
   configuration
   api/modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
