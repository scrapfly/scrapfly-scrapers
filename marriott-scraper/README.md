# Marriott.com Scraper

This scraper is using [scrapfly.io](https://scrapfly.io/) and Python to scrape hotel data from Marriott.com.

Marriott.com can be difficult to scrape because of scraper blocking and heavy JavaScript rendering, so this scraper uses Scrapfly's [Unblocker](https://scrapfly.io/docs/scrape-api/unblocker) feature with JavaScript rendering and residential proxies.

The scraping code is located in the `marriott.py` file. It's fully documented and simplified for educational purposes and the example scraper run code can be found in `run.py` file.

This scraper scrapes:
- Marriott hotel search for finding hotels in a destination for given dates:
    - hotel name, brand, location, distance, rating and review count, thumbnail, lowest price
- Marriott hotel details for:
    - address, phone, description, check-in and check-out times, pet and smoking policies

For output examples see the `./results` directory.

## Fair Use Disclaimer

Note that this code is provided free of charge as is, and Scrapfly does __not__ provide free web scraping support or consultation. For any bugs, see the issue tracker.

## Setup and Use

This Marriott scraper uses __Python 3.10__ with [scrapfly-sdk](https://pypi.org/project/scrapfly-sdk/) package which is used to scrape and parse Marriott's data.

0. Ensure you have __Python 3.10__ and [poetry Python package manager](https://python-poetry.org/docs/#installation) on your system.
1. Retrieve your Scrapfly API key from <https://scrapfly.io/dashboard> and set `SCRAPFLY_KEY` environment variable:
    ```shell
    $ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
    ```
2. Clone and install Python environment:
    ```shell
    $ git clone https://github.com/scrapfly/scrapfly-scrapers.git
    $ cd scrapfly-scrapers/marriott-scraper
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
    # or specific scraping areas
    $ poetry run pytest test.py -k test_search_scraping
    $ poetry run pytest test.py -k test_hotel_scraping
    ```
