# App Store Scraper

This scraper uses [scrapfly.io](https://scrapfly.io/) and Python to scrape app data from apps.apple.com and itunes.apple.com (Apple App Store).

The scraping code is in `app_store.py`. Example usage is in `run.py`.

This scraper scrapes:
- App metadata (iTunes lookup API, with apps.apple.com fallback)
- App reviews (iTunes customer reviews RSS feed)

For output examples see the `./results` directory.

## Fair Use Disclaimer

Note that this code is provided free of charge as is, and Scrapfly does __not__ provide free web scraping support or consultation. For any bugs, see the issue tracker.

## Setup and Use

This scraper uses __Python 3.10__ with [scrapfly-sdk](https://pypi.org/project/scrapfly-sdk/).

0. Ensure you have __Python 3.10__ and [poetry](https://python-poetry.org/docs/#installation) installed.
1. Set your Scrapfly API key:
    ```shell
    $ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
    ```
2. Install dependencies:
    ```shell
    $ cd app-store-scraper
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
    $ poetry run pytest test.py -k scrape_app_metadata
    $ poetry run pytest test.py -k scrape_reviews

    ```
