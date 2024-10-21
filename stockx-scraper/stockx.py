"""
This is an example web scraper for StockX.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-stockx/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import math
import os
from nested_lookup import nested_lookup
from typing import Dict, List

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # StockX.com requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "render_js": True,
    "proxy_pool": "public_residential_pool",
    "country": "US"
}


def parse_nextjs(result: ScrapeApiResponse) -> Dict:
    """extract nextjs cache from page"""
    data = result.selector.css("script#__NEXT_DATA__::text").get()
    if not data:
        data = result.selector.css("script[data-name=query]::text").get()
        data = data.split("=", 1)[-1].strip().strip(";")
    data = json.loads(data)
    return data


def parse_pricing(result: ScrapeApiResponse, sku: str = None) -> Dict:
    """extractproduct data from xhr responses"""
    _xhr_calls = result.scrape_result["browser_data"]["xhr_call"]
    json_calls = []
    for xhr in _xhr_calls:
        if xhr["response"]["body"] is None:
            continue
        try:
            data = json.loads(xhr["response"]["body"])
        except json.JSONDecodeError:
            continue
        json_calls.append(data)

    for xhr in json_calls:
        if "data" not in xhr or "product" not in xhr["data"] or "uuid" not in xhr["data"]["product"]:
            continue
        if sku == xhr["data"]["product"]["uuid"]:
            data = xhr["data"]["product"]
            return {
                "minimumBid": data["minimumBid"],
                "market": data["market"],
                "variants": data["variants"],
            }
    return None



async def scrape_product(url: str) -> Dict:
    """scrape a single stockx product page for product data"""
    log.info("scraping product {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(
        url, **BASE_CONFIG, rendering_wait=5000, wait_for_selector="//h2[@data-testid='trade-box-buy-amount']"
    ))
    data = parse_nextjs(result)
    # extract all products datasets from page cache
    products = nested_lookup("product", data)
    # find the current product dataset
    try:
        product = next(p for p in products if p.get("urlKey") in result.context["url"])
        product["pricing"] = parse_pricing(result, product["id"])
    except StopIteration:
        raise ValueError("Could not find product dataset in page cache", result.context)
    return product


async def scrape_search(url: str, max_pages: int = 25) -> List[Dict]:
    """Scrape StockX search"""
    log.info("scraping search {}", url)
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    # parse first page for product search data and total amount of pages:
    data = parse_nextjs(first_page)
    _first_page_results = nested_lookup("results", data)[0]
    _paging_info = _first_page_results["pageInfo"]
    total_pages = _paging_info["pageCount"] or math.ceil(_paging_info["total"] / _paging_info["limit"])
    if max_pages < total_pages:
        total_pages = max_pages

    product_previews = [edge["node"] for edge in _first_page_results["edges"]]

    # then scrape other pages concurrently:
    log.info("scraping search {} pagination ({} more pages)", url, total_pages - 1)
    _other_pages = [
        ScrapeConfig(f"{first_page.context['url']}&page={page}", **BASE_CONFIG) 
        for page in range(2, total_pages + 1)
    ]
    async for result in SCRAPFLY.concurrent_scrape(_other_pages):
        data = parse_nextjs(result)
        _page_results = nested_lookup("results", data)[0]
        product_previews.extend([edge["node"] for edge in _page_results["edges"]])
    log.info("scraped {} products from {}", len(product_previews), url)
    return product_previews
