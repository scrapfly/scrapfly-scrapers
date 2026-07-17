# Lowes.com Scraper

This scraper uses [scrapfly.io](https://scrapfly.io/) and Python to scrape data from Lowes.com.

The scraping code is in `lowes.py`. Example run code is in `run.py`.

This scraper scrapes:
- Lowes product pages
- Lowes search pages
- Lowes store locations

For output examples see the `./results` directory.

## Fair Use Disclaimer

Note that this code is provided free of charge as is, and Scrapfly does __not__ provide free web scraping support or consultation. For any bugs, see the issue tracker.

## Setup and Use

This Lowes.com scraper uses __Python 3.10__ with [scrapfly-sdk](https://pypi.org/project/scrapfly-sdk/).

0. Ensure you have __Python 3.10__ and [poetry](https://python-poetry.org/docs/#installation) on your system.
1. Set your Scrapfly API key from <https://scrapfly.io/dashboard>:
    ```shell
    $ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
    ```
2. Clone and install:
    ```shell
    $ git clone https://github.com/scrapfly/scrapfly-scrapers.git
    $ cd scrapfly-scrapers/lowes-scraper
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
