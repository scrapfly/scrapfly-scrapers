# Goodreads Scraper

This scraper uses [scrapfly.io](https://scrapfly.io/) and Python to scrape book data, ratings and reviews from Goodreads.com.

The scraping code is in `goodreads.py`. Example run code is in `run.py`.

This scraper scrapes:
- Goodreads book pages, from their JSON-LD `Book` block and the page markup
- Goodreads book reviews, the review sample a book page ships with, from its `__NEXT_DATA__` Apollo records
- Goodreads list pages, which turn a public list into book stubs and book URLs
- Goodreads book search results, which use the same row markup as list pages

For output examples see the `./results` directory.

## Fair Use Disclaimer

Note that this code is provided free of charge as is, and Scrapfly does __not__ provide free web scraping support or consultation. For any bugs, see the issue tracker.

## Setup and Use

This Goodreads scraper uses __Python 3.10__ with [scrapfly-sdk](https://pypi.org/project/scrapfly-sdk/).

0. Ensure you have __Python 3.10__ and [poetry](https://python-poetry.org/docs/#installation) on your system.
1. Set your Scrapfly API key from <https://scrapfly.io/dashboard>:
    ```shell
    $ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
    ```
2. Clone and install:
    ```shell
    $ git clone https://github.com/scrapfly/scrapfly-scrapers.git
    $ cd scrapfly-scrapers/goodreads-scraper
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
