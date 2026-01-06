# AutoScout24.com Scraper

This scraper is using [scrapfly.io](https://scrapfly.io/) and Python to scrape car listings and car details from AutoScout24.com. 

Full tutorial <https://scrapfly.io/blog/posts/how-to-scrape-autoscout24>

The scraping code is located in the `autoscout24.py` file. It's fully documented and simplified for educational purposes and the example scraper run code can be found in `run.py` file.

This scraper scrapes:
- AutoScout24 car listings from category/search pages
- AutoScout24 individual car detail pages with specifications, features, and seller information

For output examples see the `./results` directory.

## Fair Use Disclaimer

Note that this code is provided free of charge as is, and Scrapfly does __not__ provide free web scraping support or consultation. For any bugs, see the issue tracker.

## Setup and Use

This AutoScout24.com scraper uses __Python 3.10__ with [scrapfly-sdk](https://pypi.org/project/scrapfly-sdk/) package which is used to scrape and parse AutoScout24's data.

0. Ensure you have __Python 3.10__ and [poetry Python package manager](https://python-poetry.org/docs/#installation) on your system.
1. Retrieve your Scrapfly API key from <https://scrapfly.io/dashboard> and set `SCRAPFLY_KEY` environment variable:
    ```shell
    $ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
    ```
2. Clone and install Python environment:
    ```shell
    $ git clone https://github.com/scrapfly/scrapfly-scrapers.git
    $ cd scrapfly-scrapers/autoscout24-scraper
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
    $ poetry run pytest test.py -k test_listings_scraping
    $ poetry run pytest test.py -k test_car_details_scraping
    ```

