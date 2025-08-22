"""
This is an example web scraper for homegate.ch.

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
    """parse data from script tags"""
    selector = response.selector
    next_data = selector.xpath("//script[contains(text(),'window.__INITIAL_STATE__')]/text()").get()
    if not next_data:
        return
    next_data_json = json.loads(next_data.split("=", 1)[1].strip())

    return next_data_json


async def scrape_properties(urls: List[str]) -> List[Dict]:
    """scrape listing data from homegate proeprty pages"""
    # add the property pages in a scraping list
    to_scrape = [ScrapeConfig(url, asp=True, country="CH") for url in urls]
    properties = []
    # scrape all property pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_next_data(response)
        # handle expired property pages
        try:
            properties.append(data["listing"]["listing"])
        except:
            print("expired propery page")
            pass
    log.info(f"scraped {len(properties)} property listings")
    return properties


async def scrape_search(url: str, scrape_all_pages: bool, max_scrape_pages: int = 10) -> List[Dict]:
    """scrape listing data from homegate search pages"""
    # scrape the first search page first
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, asp=True, country="CH"))
    log.info("scraping search page {}", url)
    data = parse_next_data(first_page)["resultList"]["search"]["fullSearch"]["result"]
    search_data = data["listings"]
    # get the number of maximum search pages available
    max_search_pages = data["pageCount"]
    if scrape_all_pages == False and max_scrape_pages < max_search_pages:
        total_pages = max_scrape_pages
    # scrape all available pages in the search if scrape_all_pages = True or max_pages > total_search_pages
    else:
        total_pages = max_search_pages
    log.info("scraping search {} pagination ({} more pages)", url, total_pages - 1)
    # add the remaining search pages in a scraping list
    other_pages = [
        ScrapeConfig(first_page.context["url"] + f"?ep={page}", asp=True, country="CH")
        for page in range(2, total_pages + 1)
    ]
    # scrape the remaining search pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        data = parse_next_data(response)
        search_data.extend(data["resultList"]["search"]["fullSearch"]["result"]["listings"])
    log.info("scraped {} proprties from {}", len(search_data), url)
    return search_data
