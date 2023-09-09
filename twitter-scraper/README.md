# Twitter.com Scraper

This scraper is using [scrapfly.io](https://scrapfly.io/) and Python to scrape Twitter tweet, user and topic data.

Full tutorial <https://scrapfly.io/blog/how-to-scrape-twitter/>

The scraping code is located in the `twitter.py` file. It's fully documented and simplified for educational purposes and the example scraper run code can be found in `run.py` file.

This scraper scrapes:
- Twitter.com Tweet data
- Twitter.com user profile data
- Twitter.com Tweet discovery through Twitter topics

For output examples see the `./results` directory.

Note: This scraper is only scraping public Twitter data that doesn't require a login to access.

## Setup and Use

This Twitter.com scraper uses __Python 3.10__ with [scrapfly-sdk](https://pypi.org/project/scrapfly-sdk/) package which is used to scrape and parse Twitter's data.

1. Retrieve your Scrapfly API key from <https://scrapfly.io/dashboard> and set `SCRAPFLY_KEY` environment variable:
    ```shell
    $ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
    ```
2. Clone and install Python environment:
    ```shell
    $ git clone https://github.com/scrapfly/scrapfly-scrapers.git
    $ cd scrapfly-scrapers/twitter-scraper
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
    $ poetry run pytest test.py -k test_tweet_scraping
    $ poetry run pytest test.py -k test_topic_scraping
    ```

