"""
This is an example web scraper for seloger.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import json
import re
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from typing import Dict, List
from pathlib import Path
from loguru import logger as log

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "fr",
    "proxy_pool": "public_residential_pool",
    "render_js": True,
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


def parse_search(result: ScrapeApiResponse):
    """parse property listing data from seloger search pages"""
    # select the script tag from the HTML
    selector = result.selector
    data = []
    for i in selector.xpath("//div[@data-testid='serp-core-classified-card-testid']"):
        # If the card doesn't have a main link, it's an empty placeholder, so we skip it.
        if not i.xpath(".//a[@data-testid='card-mfe-covering-link-testid']/@href").get():
            continue

        data.append(
            {
                "title": i.xpath(".//a[@data-testid='card-mfe-covering-link-testid']/@title").get(),
                "url": i.xpath(".//a[@data-testid='card-mfe-covering-link-testid']/@href").get(),
                "images": i.xpath(".//div[contains(@data-testid, 'cardmfe-picture')]//img/@src").getall(),
                "price": i.xpath(".//div[contains(@data-testid, 'cardmfe-price')]/@aria-label").get(),
                "price_per_m2": i.xpath(
                    ".//div[contains(@data-testid, 'cardmfe-price')]//span[contains(text(),'m²')]/text()"
                ).get(),
                "property_facts": i.xpath(
                    ".//div[contains(@data-testid, 'keyfacts')]/div[text() != '·']/text()"
                ).getall(),
                "address": i.xpath(".//div[contains(@data-testid, 'address')]//text()").get(),
                "agency": i.xpath(
                    ".//div[contains(@data-testid, 'cardmfe-bottom')]/div//span[not(contains(text(), 'sur SeLoger Neuf'))]/text()"
                ).get(),
            }
        )

    max_results = result.selector.xpath("//h1[contains(@data-testid, 'serp-title')]/text()").get()
    max_results = int(re.sub(r"\D", "", max_results)) if re.search(r"\d", max_results) else max_results
    return {"results": data, "max_results": max_results}


def parse_property_page(result: ScrapeApiResponse):
    """parse property data from the nextjs cache"""
    # select the script tag from the HTML
    script_text = result.selector.css("body > script:nth-child(7)::text").get()
    if '["__UFRN_LIFECYCLE_SERVERREQUEST__"]' not in script_text:
        raise ValueError("The script tag does not contain the expected window JSON assignment")

    pattern = r'window\["__UFRN_LIFECYCLE_SERVERREQUEST__"\]=JSON\.parse\("(.+)"\);?'

    match = re.search(pattern, script_text, re.DOTALL)
    if not match:
        raise ValueError("Could not extract JSON string from script tag")
    json_str_escaped = match.group(1)
    json_str = json_str_escaped.encode("utf-8").decode("unicode_escape")
    listing_data = json.loads(json_str)
    listing_data = listing_data["app_cldp"]["data"]["classified"]
    return listing_data


async def scrape_search(
    url: str,
    max_pages: int = 10,
) -> List[Dict]:
    """
    scrape seloger search pages, which supports pagination by adding a LISTING-LISTpg parameter at the end of the URL
    https://www.seloger.com/classified-search?distributionTypes=Buy&estateTypes=Apartment&locations=AD08FR13100&page=page_number
    """
    log.info("scraping search page {}", url)
    # scrape the first page first
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    search_page_result = parse_search(first_page)
    # extract the property listing data
    search_data = search_page_result["results"]
    # get the max search pages number
    total_search_pages = search_page_result["max_results"] // 30  # 30 results per page
    # get the number of pages to scrape
    if max_pages and max_pages <= total_search_pages:
        total_search_pages = max_pages

    log.info("scraping search {} pagination ({} more pages)", url, total_search_pages - 1)
    # add the ramaining pages in a scraping list
    _other_pages = [
        ScrapeConfig(first_page.context["url"] + f"&page={page}", **BASE_CONFIG)
        for page in range(2, total_search_pages + 1)
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
