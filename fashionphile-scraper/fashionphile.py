"""
This is an example web scraper for fashionphile.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
from typing import Dict, List
from pathlib import Path
from loguru import logger as log
from urllib.parse import parse_qs, urlencode, urlparse
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass fashionphile.com web scraping blocking
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
    """scrape fashionphile product pages for product data"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    products = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = find_hidden_data(response)
        product = data["props"]["pageProps"]["initialState"]["productPageReducer"]["productData"]
        products.append(product)
    log.success(f"scraped {len(products)} product listings from product pages")
    return products


def update_url_parameter(url, **params):
    """update url query parameter of an url with new values"""
    current_params = parse_qs(urlparse(url).query)
    updated_query_params = urlencode({**current_params, **params}, doseq=True)
    return f"{url.split('?')[0]}?{updated_query_params}"


async def scrape_search(url: str, max_pages: int = 10) -> List[Dict]:
    log.info(f"scraping search page {url}")
    # scrape first page
    result_first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data_first_page = find_hidden_data(result_first_page)
    data_first_page = data_first_page["props"]["pageProps"]["serverState"]["initialResults"][
        "prod_ecom_products_date_desc"
    ]["results"][0]
    results = data_first_page["hits"]

    # find total page count
    total_pages = data_first_page["nbPages"]
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    # scrape remaining pages
    log.info(f"scraping search pagination ({total_pages-1} more pages)")
    to_scrape = [
        ScrapeConfig(update_url_parameter(url, page=page), **BASE_CONFIG) for page in range(2, total_pages + 1)
    ]
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        data = find_hidden_data(result)
        data = data["props"]["pageProps"]["serverState"]["initialResults"]["prod_ecom_products_date_desc"]["results"][0]
        results.extend(data["hits"])
    log.success(f"scraped {len(results)} product listings from search pages")
    return results
