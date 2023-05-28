# Zillow.com Scraper

This scraper is using [scrapfly.io](https://scrapfly.io/) and Python to scrape property data from Zillow.com. 

Full tutorial <https://scrapfly.io/blog/how-to-scrape-zillow/>

The scraping code is located in the `zillow.py` file. It's fully documented and simplified for educational purposes and the example scraper run code can be found in `run.py` file.

This scraper scrapes:
- Zillow search for finding property listings
- Zillow property pages for property datasets

For output examples see the `./results` directory.

## Setup and Use

This Zillow scraper is using Python with [scrapfly-sdk](https://pypi.org/project/scrapfly-sdk/) package which is used to scrape and parse Zillow's data.

1. Retrieve your Scrapfly API key from <https://scrapfly.io/dashboard> and set `SCRAPFLY_KEY` environment variable:
    ```shell
    $ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
    ```
2. Clone and install Python environment:
    ```shell
    $ git clone git@github.com:scrapfly/scrapfly-scrapers.git
    $ cd scrapfly-scrapers/zillow-scraper
    $ poetry install .
    ```
3. Run example scrape:
    ```shell
    $ poetry run python run.py
    ```
4. Run tests:
    ```shell
    $ poetry install --with dev
    $ poetry run pytest test.py
    # or specific scraping areas
    $ poetry run pytest test.py -k test_search_scraping
    $ poetry run pytest test.py -k test_property_scraping
    ```

