# TikTok.com Scraper

This scraper is using [scrapfly.io](https://scrapfly.io/) and Python to scrape data from tiktok.com. 

Full tutorial <https://scrapfly.io/blog/how-to-scrape-tiktok-python-json/>

The scraping code is located in the `tiktok.py` file. It's fully documented and simplified for educational purposes and the example scraper run code can be found in `run.py` file.

This scraper scrapes:
- TikTok post pages for post/video data.
- TikTok comments for comment data on a specific post/video.
- TikTok profile pages for profile data.
- TikTok channel pages for video data.
- TikTok search pages for video data on search results. It can scrape profiles as well.

For output examples see the `./results` directory.

## Fair Use Disclaimer

Note that this code is provided free of charge as is, and Scrapfly does __not__ provide free web scraping support or consultation. For any bugs, see the issue tracker.

## Setup and Use

This TikTok.com scraper uses __Python 3.10__ with [scrapfly-sdk](https://pypi.org/project/scrapfly-sdk/) package which is used to scrape and parse TikTok's data.

0. Ensure you have __Python 3.10__ and [poetry Python package manager](https://python-poetry.org/docs/#installation) on your system.
1. Retrieve your Scrapfly API key from <https://scrapfly.io/dashboard> and set `SCRAPFLY_KEY` environment variable:
    ```shell
    $ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
    ```
2. Clone and install Python environment:
    ```shell
    $ git clone https://github.com/scrapfly/scrapfly-scrapers.git
    $ cd scrapfly-scrapers/tiktok-scraper
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
    $ poetry run pytest test.py -k test_comment_scraping
    $ poetry run pytest test.py -k test_post_scraping
    $ poetry run pytest test.py -k test_profile_scraping
    $ poetry run pytest test.py -k test_search_scraping
    $ poetry run pytest test.py -k test_channel_scraping
    ```
