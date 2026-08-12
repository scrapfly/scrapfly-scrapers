# Pinterest.com Scraper

This scraper is using [scrapfly.io](https://scrapfly.io/) and Python to scrape data from Pinterest.com.

The scraping code is located in the `pinterest.py` file. It's fully documented and simplified for educational purposes and the example scraper run code can be found in `run.py` file.

This scraper scrapes:
- Pinterest.com search results for pin data including titles, descriptions, images, videos, destination links, board names, and owner usernames
- Pinterest.com boards (`/<user>/<board>/`) for board metadata and their pins
- Pinterest.com profiles (`/<user>/`) for profile metadata and the user's pins
- Pinterest.com pin detail pages (`/pin/<id>/`) for full pin data
- Bulk pin image downloads to a local directory

For output examples see the `./results` directory.

## Fair Use Disclaimer

Note that this code is provided free of charge as is, and Scrapfly does __not__ provide free web scraping support or consultation. For any bugs, see the issue tracker.

## Setup and Use

This Pinterest.com scraper uses __Python 3.10__ with [scrapfly-sdk](https://pypi.org/project/scrapfly-sdk/) package which is used to scrape and parse Pinterest's data.

0. Ensure you have __Python 3.10__ and [poetry Python package manager](https://python-poetry.org/docs/#installation) on your system.
1. Retrieve your Scrapfly API key from <https://scrapfly.io/dashboard> and set `SCRAPFLY_KEY` environment variable:
    ```shell
    $ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
    ```
2. Clone and install Python environment:
    ```shell
    $ git clone https://github.com/scrapfly/scrapfly-scrapers.git
    $ cd scrapfly-scrapers/pinterest-scraper
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
    $ poetry run pytest test.py -k test
    $ poetry run pytest test.py -k test_board_scraping
    $ poetry run pytest test.py -k test_profile_scraping
    $ poetry run pytest test.py -k test_pin_scraping
    $ poetry run pytest test.py -k test_download_images
    ```

## How It Works

Pinterest's board and profile pages server-render a resource cache (embedded in
the page's `__PWS_INITIAL_PROPS__` script tag) containing the first page of
data. Additional pages are fetched from Pinterest's internal
`/resource/<Name>/get/` API, authorized with the `csrftoken` cookie and
`x-app-version` header captured from that same browser session — no login
required, since this is all public data.

Pin detail pages don't expose this resource cache, so `scrape_pin` parses the
rendered DOM directly instead.
