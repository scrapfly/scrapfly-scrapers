"""
This is an example web scraper for immoscout24.ch.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import json
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from typing import Dict, List
from pathlib import Path
from loguru import logger as log

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass web scraping blocking
    "asp": True,
    # set the proxy country to switzerland
    "country": "CH",
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


def parse_next_data(response: ScrapeApiResponse) -> Dict:
    """parse listing data from script tags"""
    selector = response.selector
    # extract data in JSON from script tags
    script = selector.xpath("//script[@id='state']/text()").get()
    if not script:
        return
    next_data = script.strip("__INITIAL_STATE__=")
    # replace undefined values
    next_data = next_data.replace("undefined", "null")
    next_data_json = json.loads(next_data)
    return next_data_json


async def scrape_properties(urls: List[str]) -> List[Dict]:
    """scrape listing data from immoscout24 proeprty pages"""
    # add the property pages in a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    properties = []
    # scrape all property pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_next_data(response)
        # handle expired property pages
        try:
            properties.append(data["pages"]["detail"]["propertyDetails"])
        except:
            log.info("expired property page")
            pass
    log.info(f"scraped {len(properties)} property listings")
    return properties


async def scrape_search(
    url: str, scrape_all_pages: bool, max_scrape_pages: int = 10
) -> List[Dict]:
    """scrape listing data from immoscout24 search pages"""
    # scrape the first search page first
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    log.info("scraping search page {}", url)
    data = parse_next_data(first_page)["pages"]["searchResult"]["resultData"]
    search_data = data["listData"]
    # get the number of maximum search pages available
    max_search_pages = data["pagingData"]["totalPages"]
     # scrape all available pages in the search if scrape_all_pages = True or max_pages > total_search_pages
    if scrape_all_pages == False and max_scrape_pages < max_search_pages:
        total_pages = max_scrape_pages
    else:
        total_pages = max_search_pages
    log.info("scraping search {} pagination ({} more pages)", url, total_pages - 1)
    # add the remaining search pages in a scraping list
    other_pages = [
        ScrapeConfig(first_page.context["url"] + f"?pn={page}", asp=True, country="CH")
        for page in range(2, total_pages + 1)
    ]
    # scrape the remaining search pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        data = parse_next_data(response)
        search_data.extend(
            data["pages"]["searchResult"]["resultData"]["listData"]
        )
    log.info("scraped {} proprties from {}", len(search_data), url)
    return search_data
