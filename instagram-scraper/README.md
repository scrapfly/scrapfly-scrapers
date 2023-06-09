# Instagram.com Scraper

This scraper is using [scrapfly.io](https://scrapfly.io/) and Python to scrape user and user post datasets from Instagram.com

Full tutorial <https://scrapfly.io/blog/how-to-scrape-instagram/>

The scraping code is located in the `instagram.py` file. It's fully documented and simplified for educational purposes and the example scraper run code can be found in `run.py` file.

This scraper scrapes:
- Instagram.com user information  
- Instagram.com user posts  

For output examples see the `./results` directory.

Note: This scraper is only scraping public Instagram data that doesn't require a login to access.

## Setup and Use

This Instagram.com scraper is using Python with [scrapfly-sdk](https://pypi.org/project/scrapfly-sdk/) package which is used to scrape and parse Instagram's data.

1. Retrieve your Scrapfly API key from <https://scrapfly.io/dashboard> and set `SCRAPFLY_KEY` environment variable:
    ```shell
    $ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
    ```
2. Clone and install Python environment:
    ```shell
    $ git clone git@github.com:scrapfly/scrapfly-scrapers.git
    $ cd scrapfly-scrapers/crunchbase-scraper
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
    $ poetry run pytest test.py -k test_user_scraping
    $ poetry run pytest test.py -k test_post_scraping
    $ poetry run pytest test.py -k test_user_post_scraping
    ```

