# Immowelt.de Scraper

This scraper is using [scrapfly.io](https://scrapfly.io/) and Python to scrape property listing data from Immowelt.de. 

Full tutorial  

The scraping code is located in the `immowelt.py` file. It's fully documented and simplified for educational purposes and the example scraper run code can be found in `run.py` file.

This scraper scrapes:
- Immowelt property pages for property listing data
- Immowelt property search for finding property listings  

In the property saerch scraper, you need to add `location_ids` to the API request body, which reprsents the search location. To get these ids, follow these steps:  
1. Search for properties in a specific location on immowelt.de  
2. Open developer tools and select the `Netowrk` tab then filter by `Fetch/XHR` requests  
3. Click on the next search page button to load more data  
4. You will see the request made to the search API, which named as `searches`  
5. Grab the `location_ids` from the request `Payload`:  

<img src="https://github.com/scrapfly/scrapfly-scrapers/assets/73492002/e6a80576-c6ed-4e47-9e46-6677522a5809" align="center" height="400" width="600">  
<br/><br/>

For output examples see the `./results` directory.

## Fair Use Disclaimer

Note that this code is provided free of charge as is, and Scrapfly does __not__ provide free web scraping support or consultation. For any bugs, see the issue tracker.

## Setup and Use

This Immowelt.de scraper uses __Python 3.10__ with [scrapfly-sdk](https://pypi.org/project/scrapfly-sdk/) package which is used to scrape and parse Immowelt's data.

0. Ensure you have __Python 3.10__ and [poetry Python package manager](https://python-poetry.org/docs/#installation) on your system.
1. Retrieve your Scrapfly API key from <https://scrapfly.io/dashboard> and set `SCRAPFLY_KEY` environment variable:
    ```shell
    $ export SCRAPFLY_KEY="YOUR SCRAPFLY KEY"
    ```
2. Clone and install Python environment:
    ```shell
    $ git clone https://github.com/scrapfly/scrapfly-scrapers.git
    $ cd scrapfly-scrapers/immowelt-scraper
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
    $ poetry run pytest test.py -k test_properties_scraping
    ```
