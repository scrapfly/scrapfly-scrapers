# Goibibo Scraper

This scraper is using [scrapfly.io](https://scrapfly.io/) and Python to scrape hotel and flight search data from goibibo.com.

Goibibo.com can be difficult to scrape because of scraper blocking, so this scraper uses Scrapfly's [Anti Scraping Protection Bypass](https://scrapfly.io/docs/scrape-api/anti-scraping-protection) feature, browser rendering, and session-based requests to capture and paginate Goibibo's internal listing and flight search-stream APIs.

The scraping code is located in the `goibibo.py` file. It's fully documented and simplified for educational purposes and the example scraper run code can be found in `run.py` file.

This scraper scrapes:
- Goibibo hotel search results, with pagination
- Hotel name, price, rating, amenities, location, and images
- Goibibo flight search results (one-way and round-trip)
- Flight number, airline, fare, duration, stops, and leg details

For output examples see the `./results` directory.

## Fair Use Disclaimer

Note that this code is provided free of charge as is, and Scrapfly does __not__ provide free web scraping support or consultation. For any bugs, see the issue tracker.

## Setup and Use

This Goibibo scraper uses __Python 3.10__ with [scrapfly-sdk](https://pypi.org/project/scrapfly-sdk/) package which is used to scrape and parse Goibibo hotel and flight data.

0. Ensure you have __Python 3.10__ and [poetry Python package manager](https://python-poetry.org/docs/#installation) on your system.
1. Retrieve your Scrapfly API key from <https://scrapfly.io/dashboard> and set `SCRAPFLY_KEY` environment variable:
    ```shell
    $ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
    ```
2. Clone and install Python environment:
    ```shell
    $ git clone https://github.com/scrapfly/scrapfly-scrapers.git
    $ cd scrapfly-scrapers/goibibo-scraper
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
    $ poetry run pytest test.py -k test_hotel_search_scraping
    ```
