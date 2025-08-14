"""
This is an example web scraper for Walmart.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
import math
import asyncio
from typing import Dict, List, TypedDict, Any
from urllib.parse import urlencode
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass walmart.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
    "proxy_pool": "public_residential_pool",
}


def parse_product(response: ScrapeApiResponse):
    """parse product data from walmart product pages"""
    sel = response.selector
    data = sel.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
    if not data:
        return None  # Signal failure if __NEXT_DATA__ is not found

    data = json.loads(data)
    try:
        # The key path to the product data
        _product_raw = data["props"]["pageProps"]["initialData"]["data"]["product"]
        reviews_raw = data["props"]["pageProps"]["initialData"]["data"]["reviews"]
    except KeyError:
        return None  # Signal failure if the JSON structure is unexpected

    # There's a lot of product data, so we need to do some filtering:
    wanted_product_keys = [
        "availabilityStatus",
        "averageRating",
        "brand",
        "id",
        "imageInfo",
        "manufacturerName",
        "name",
        "orderLimit",
        "orderMinLimit",
        "priceInfo",
        "shortDescription",
        "type",
    ]
    product = {k: v for k, v in _product_raw.items() if k in wanted_product_keys}
    return {"product": product, "reviews": reviews_raw}


def parse_search(response: ScrapeApiResponse) -> List[Dict]:
    """parse product listing data from search pages"""
    sel = response.selector
    data = sel.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
    data = json.loads(data)
    total_results = data["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"][0]["count"]
    results = data["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"][0]["items"]
    return {"results": results, "total_results": total_results}


async def _scrape_product_with_fallback(url: str) -> Dict[str, Any]:
    """helper that scrapes a single URL with a JS rendering fallback."""
    log.info(f"scraping product: {url}")
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    parsed_data = parse_product(response)

    if parsed_data is None:
        log.warning(f"retrying with JS rendering: {url}")
        response = await SCRAPFLY.async_scrape(ScrapeConfig(url, render_js=True, **BASE_CONFIG))
        parsed_data = parse_product(response)
        if parsed_data is None:
            log.error(f"failed to scrape product even with JS rendering: {url}")
            return {"url": url, "error": "failed to parse"}

    return parsed_data


async def scrape_products(urls: List[str]) -> List[Dict]:
    """Scrape product data from product pages with a JS rendering fallback."""
    # Create a scraping task for each URL
    to_scrape_tasks = [_scrape_product_with_fallback(url) for url in urls]

    # Run all scraping tasks concurrently
    results = await asyncio.gather(*to_scrape_tasks)

    log.success(f"scraped {len(results)} product pages")
    return results


async def scrape_search(
    query: str = "",
    sort: TypedDict(
        "SortOptions",
        {"best_seller": str, "best_match": str, "price_low": str, "price_high": str},
    ) = "best_match",
    max_pages: int = None,
):
    """scrape single walmart search page"""

    def make_search_url(page):
        url = "https://www.walmart.com/search?" + urlencode(
            {
                "q": query,
                "page": page,
                sort: sort,
                "affinityOverride": "default",
            }
        )
        return url

    # scrape the first search page
    log.info(f"scraping the first search page with the query ({query})")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(make_search_url(1), render_js=True, **BASE_CONFIG))
    data = parse_search(first_page)
    search_data = data["results"]
    total_results = data["total_results"]

    # find total page count to scrape
    total_pages = math.ceil(total_results / 40)
    # walmart sets the max search results to 25 pages
    if total_pages > 25:
        total_pages = 25
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    # then add the remaining pages to a scraping list and scrape them concurrently
    log.info(f"scraping search pagination, remaining ({total_pages - 1}) more pages")
    other_pages = [ScrapeConfig(make_search_url(page), **BASE_CONFIG) for page in range(2, total_pages + 1)]
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        search_data.extend(parse_search(response)["results"])
    log.success(f"scraped {len(search_data)} product listings from search pages")
    return search_data
