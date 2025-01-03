"""
This is an example web scraper for seloger.com.

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
    "asp": True,
    "country": "fr",
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


def parse_search(result: ScrapeApiResponse):
    """parse property listing data from seloger search pages"""
    # select the script tag from the HTML
    script_jsons = result.selector.xpath("//script[contains(., 'window[\"initialData\"]')]/text()").re(
        r'JSON.parse\("(.+?)"\)'
    )
    # decode the JSON data
    datasets = [json.loads(script_json.encode("utf-8").decode("unicode_escape")) for script_json in script_jsons]
    cards = []
    # validate the cards data to avoid advertisement cards
    for card in datasets[0]["cards"]["list"]:
        if card["cardType"] == "classified":
            cards.append(card)
    search_meta = datasets[0]["navigation"]
    return {"results": cards, "search": search_meta}


def _max_search_pages(search_meta: Dict) -> int:
    """get the maximum number of pages available on the search"""
    return search_meta["counts"]["count"] // search_meta["pagination"]["resultsPerPage"]


def parse_property_page(result: ScrapeApiResponse):
    """parse property data from the nextjs cache"""
    # select the script tag from the HTML
    next_data = result.selector.css("script[id='__NEXT_DATA__']::text").get()
    listing_data = json.loads(next_data)["props"]["pageProps"]["listingData"]
    # extract property data from the property page
    property_data = {}
    property_data["listing"] = listing_data["listing"]
    property_data["agency"] = listing_data["agency"]
    return property_data


async def scrape_search(
    url: str,
    scrape_all_pages: bool,
    max_pages: int = 10,
) -> List[Dict]:
    """
    scrape seloger search pages, which supports pagination by adding a LISTING-LISTpg parameter at the end of the URL
    https://www.seloger.com/immobilier/achat/immo-bordeaux-33/bien-appartement/?LISTING-LISTpg=page_number
    """
    log.info("scraping search page {}", url)
    # scrape the first page first
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    search_page_result = parse_search(first_page)
    # extract the property listing data
    search_data = search_page_result["results"]
    # get the max search pages number
    total_search_pages = _max_search_pages(search_page_result["search"])
    # scrape a specfic amount of search pages
    if scrape_all_pages == False and max_pages < total_search_pages:
        total_pages = max_pages
    # scrape all available pages in the search if scrape_all_pages = True or max_pages > total_search_pages
    else:
        total_pages = total_search_pages
    log.info("scraping search {} pagination ({} more pages)", url, total_pages - 1)
    # add the ramaining pages in a scraping list
    _other_pages = [
        ScrapeConfig(f"{first_page.context['url']}?LISTING-LISTpg={page}", **BASE_CONFIG)
        for page in range(2, total_pages + 1)
    ]
    # scrape the remaining pages concurrently
    async for result in SCRAPFLY.concurrent_scrape(_other_pages):
        page_data = parse_search(result)["results"]
        search_data.extend(page_data)
    log.info("scraped {} proprties from {}", len(search_data), url)
    return search_data


async def scrape_property(urls: List[str]) -> List[Dict]:
    """scrape seloger property pages"""
    data = []
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        property_data = parse_property_page(result)
        data.append(property_data)
    log.success(f"scraped {len(data)} properties from Seloger property pages")
    return data
