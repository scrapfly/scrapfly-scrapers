"""
This is an example web scraper for vestiairecollective.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
from typing import Dict, List
from pathlib import Path
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse


SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass vestiairecollective.com web scraping blocking
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


def parse_xhr_call(result: ScrapeApiResponse) -> List[Dict]:
    """extract JSON data from xhr_calls"""
    _xhr_calls = result.scrape_result["browser_data"]["xhr_call"]
    try:
        # extract the search xhr call
        search_call = [call for call in _xhr_calls if "search" in call["url"]][0]
    except:
        log.warning("couldn't find the search xhr call - is the search URL t a valid search page?")
    # extract the product listings data from the first search page
    data = json.loads(search_call["response"]["body"])
    result = {
        "headers": search_call["headers"],
        "payload": json.loads(search_call["body"]),
        "total_pages": data["paginationStats"]["totalPages"],
        "data": data["items"],
    }
    return result


async def send_api_request(headers, payload, offset) -> List[Dict]:
    """send a POST request the search API"""
    # change the offest to control the number of products to retrieve
    payload["pagination"]["offset"] = offset
    # send a POST request to the search API
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url="https://search.vestiairecollective.com/v1/product/search",
            headers=headers,
            body=json.dumps(payload),
            country="US",
            method="POST",
        )
    )
    return response


def parse_search_api(result: ScrapeApiResponse) -> List[Dict]:
    """extract JSON data from the search API response"""
    data = json.loads(result.scrape_result["content"])
    return data["items"]


async def scrape_products(urls: List[str]) -> dict:
    """scrape goat.com product pages for product data"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    products = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = find_hidden_data(response)
        product = data["props"]["pageProps"]["product"]
        products.append(product)
    log.success(f"scraped {len(products)} product listings from product pages")
    return products


async def retry_failure(url: str, _retries: int = 0):
    """retry failed requests with a maximum number of retries"""
    max_retries = 3
    try:
        response = await SCRAPFLY.async_scrape(
            ScrapeConfig(url, **BASE_CONFIG, render_js=True, proxy_pool="public_residential_pool")
        )
        if response.status_code != 200:
            if _retries < max_retries:
                log.debug("Retrying failed request")
                return await retry_failure(url, _retries=_retries + 1)
            else:
                raise Exception("Unable to scrape first search page, max retries exceeded")
        return response            
    except Exception as e:
        if _retries < max_retries:
            log.debug("Retrying failed request")
            return await retry_failure(url, _retries=_retries + 1)
        else:
            raise Exception("Unable to scrape first search page, max retries exceeded")


async def scrape_search(url: str, max_pages: int = 10) -> List[Dict]:
    log.info(f"scraping search page {url}")
    # first, scrape the first search page while enabling render_js to capture the xhr calls
    result_first_page = await retry_failure(url)
    # then, parse the first page response to get the headers, payload, data and the number of total pages
    first_page_api_result = parse_xhr_call(result_first_page)
    headers = first_page_api_result["headers"]
    payload = first_page_api_result["payload"]
    results = first_page_api_result["data"]
    total_pages = first_page_api_result["total_pages"]

    # find total page count
    if max_pages and max_pages < total_pages:
        total_pages = max_pages
    total_products = total_pages * 48  # each page contains 48 listings

    # next, scrape the remaining search pages directly from the API
    log.info(f"scraping search pagination, remaining ({total_pages - 1}) more pages")
    for offset in range(48, total_products, 48):
        try:        
            result = await send_api_request(headers, payload, offset)
            results.extend(parse_search_api(result))
        except Exception as e:
            log.debug(f"Error occured while requesting search API: {e}")
            pass            
    log.success(f"scraped {len(results)} product listings from search pages")
    return results
