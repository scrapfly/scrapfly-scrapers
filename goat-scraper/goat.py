"""
This is an example web scraper for goat.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
import math
from datetime import datetime
from uuid import uuid4
from typing import Dict, List
from pathlib import Path
from loguru import logger as log
from urllib.parse import quote, urlencode
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse


SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass goat.com web scraping blocking(cloudflare)
    "asp": True,
    # set the proxy country to US
    "country": "US",
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


def find_hidden_data(result: ScrapeApiResponse) -> dict:
    """extract hidden NEXT_DATA from page html"""
    data = result.selector.css("script#__NEXT_DATA__::text").get()
    data = json.loads(data)
    return data


async def scrape_products(urls: List[str]) -> dict:
    """scrape goat.com product pages for product data"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    products = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = find_hidden_data(response)
        product = data["props"]["pageProps"]["productTemplate"]
        if data["props"]["pageProps"]["offers"]:
            product["offers"] = data["props"]["pageProps"]["offers"]["offerData"]
        else:
            product["offers"] = None
        products.append(product)
    log.success(f"scraped {len(products)} product listings from product pages")
    return products


async def scrape_search(query: str, max_pages: int = 10) -> List[Dict]:
    """Scrape goat.com search pages for product listings using the new web-api."""

    def make_page_url(page: int = 1):
        params = {
            "queryString": query,
            "pageLimit": "12",
            "pageNumber": page,
            "sortType": "1",
        }
        return f"https://www.goat.com/web-api/consumer-search/get-product-search-results?{urlencode(params)}"

    url_first_page = make_page_url(page=1)
    log.info(f"Scraping product search with query '{query}'")
    result_first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url=url_first_page, **BASE_CONFIG))
    first_page_data = json.loads(result_first_page.content)["data"]
    results = first_page_data.get("productsList", [])
    total_results = first_page_data.get("totalResults", 0)
    results_per_page = 12
    total_pages = math.ceil(total_results / results_per_page)

    if max_pages and max_pages < total_pages:
        total_pages = max_pages
    if total_pages > 1:
        log.info(f"Scraping search pagination ({total_pages-1} more pages)")
        to_scrape = [ScrapeConfig(make_page_url(page=page), **BASE_CONFIG) for page in range(2, total_pages + 1)]
        async for result in SCRAPFLY.concurrent_scrape(to_scrape):
            data = json.loads(result.content).get("data", {})
            items = data.get("productsList", [])
            results.extend(items)
    log.success(f"Scraped {len(results)} product listings from search")
    return results
