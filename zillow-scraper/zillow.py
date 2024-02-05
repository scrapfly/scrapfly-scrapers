"""
This is an example web scraper for zillow.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-zillow/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
import random
import re
from typing import List
from urllib.parse import quote, urlencode

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Zillow.com requires Anti Scraping Protection bypass feature:
    "asp": True,
    "country": "US",
}


async def scrape_search(url: str) -> List[dict]:
    """base search function which is used by sale and rent search functions"""
    log.info(f"scraping search: {url}")
    # first scrape the search HTML page and find query variables for this search
    html_result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    script_data = json.loads(html_result.selector.xpath("//script[@id='__NEXT_DATA__']/text()").get())
    query_data = script_data["props"]["pageProps"]["searchPageState"]["queryState"]
    full_query = {
        "searchQueryState": query_data,
        "wants": {"cat1": ["listResults", "mapResults"], "cat2": ["total"]},
        "requestId": random.randint(2, 10),
    }
    # then scrape Zillow's backend API for all query results:
    _backend_url = "https://www.zillow.com/async-create-search-page-state"
    api_result = await SCRAPFLY.async_scrape(
        ScrapeConfig(_backend_url, **BASE_CONFIG, headers={"content-type": "application/json"},
                      body=json.dumps(full_query), method="PUT")
    )
    data = json.loads(api_result.content)
    _total = data["categoryTotals"]["cat1"]["totalResultCount"]
    if _total > 500:
        log.warning(f'more than 500 results ({_total}) for query "{url}" ')
    return data["cat1"]["searchResults"]["mapResults"]


async def scrape_properties(urls: List[str]):
    """scrape zillow property pages for property data"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    results = []
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        data = result.selector.css("script#__NEXT_DATA__::text").get()
        if data:
            # Option 1: some properties are located in NEXT DATA cache
            data = json.loads(data)
            property_data = json.loads(data["props"]["pageProps"]["componentProps"]["gdpClientCache"])
            property_data = property_data[list(property_data)[0]]['property']
        else:
            # Option 2: other times it's in Apollo cache
            data = result.selector.css("script#hdpApolloPreloadedData::text").get()
            data = json.loads(json.loads(data)["apiCache"])
            property_data = next(v["property"] for k, v in data.items() if "ForSale" in k)
        results.append(property_data)
    return results
