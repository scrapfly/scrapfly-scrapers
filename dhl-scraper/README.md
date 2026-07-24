# DHL Scraper

This scraper is using [scrapfly.io](https://scrapfly.io/) and Python to scrape shipment tracking data from dhl.com.

DHL can be difficult to scrape because of scraper blocking, so this scraper uses Scrapfly's [Anti Scraping Protection Bypass](https://scrapfly.io/docs/scrape-api/anti-scraping-protection) feature with JavaScript rendering and residential proxies.

The scraping code is located in the `dhl.py` file. Example usage can be found in `run.py`.

This scraper scrapes:
- DHL shipment tracking by tracking number

For output examples see the `./results` directory.

## Fair Use Disclaimer

Note that this code is provided free of charge as is, and Scrapfly does __not__ provide free web scraping support or consultation. For any bugs, see the issue tracker.

## Setup and Use

This DHL scraper uses __Python 3.10__ with [scrapfly-sdk](https://pypi.org/project/scrapfly-sdk/) package.

0. Ensure you have __Python 3.10__ and [poetry Python package manager](https://python-poetry.org/docs/#installation) on your system.
1. Retrieve your Scrapfly API key from <https://scrapfly.io/dashboard> and set `SCRAPFLY_KEY` environment variable:
    ```shell
    $ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
    ```
2. Clone and install Python environment:
    ```shell
    $ git clone https://github.com/scrapfly/scrapfly-scrapers.git
    $ cd scrapfly-scrapers/dhl-scraper
    $ poetry install
    ```
3. Run example scrape:
    ```shell
    $ poetry run python run.py
    ```
4. Run tests:
    ```shell
    $ poetry install --with dev
    $ poetry run pytest test.py
    ```
