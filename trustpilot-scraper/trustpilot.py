"""
This is an example web scraper for trustpilot.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import json
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from typing import Dict, List
from loguru import logger as log

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass trustpilot web scraping blocking
    "asp": True,
    # set the poxy location to US
    "country": "US",
}


def parse_hidden_data(response: ScrapeApiResponse):
    """parse JSON data from script tags"""
    selector = response.selector
    script = selector.xpath("//script[@id='__NEXT_DATA__']/text()").get()
    data = json.loads(script)
    return data


def parse_company_data(data: Dict) -> Dict:
    """parse company data from JSON and execlude the web app details"""
    data = data["props"]["pageProps"]
    return {
        "pageUrl": data["pageUrl"],
        "companyDetails": data["businessUnit"],
        "reviews": data["reviews"],
    }


async def scrape_company(urls: List[str]) -> List[Dict]:
    """scrape trustpilot company pages"""
    companies = []
    # add the company pages to a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    # scrape all the company pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_hidden_data(response)
        data = parse_company_data(data)
        companies.append(data)
    log.success(f"scraped {len(companies)} company listings from company pages")
    return companies


async def scrape_search(url: str, max_pages: int = None) -> List[Dict]:
    """scrape trustpilot search pages"""
    # scrape the first search page first
    log.info("scraping the first search page")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_hidden_data(first_page)["props"]["pageProps"]["businessUnits"]
    search_data = data["businesses"]

    # get the number of pages to scrape
    total_pages = data["totalPages"]
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    log.info(f"scraping search pagination ({total_pages - 1} more pages)")
    # add the remaining search pages in a scraping list
    other_pages = [
        ScrapeConfig(url + f"?page={page_number}", **BASE_CONFIG)
        for page_number in range(2, total_pages + 1)
    ]
    # scrape the remaining search pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        data = parse_hidden_data(response)["props"]["pageProps"]["businessUnits"]["businesses"]
        search_data.extend(data)
    log.success(f"scraped {len(search_data)} company listings from search")
    return search_data


async def get_reviews_api_url(url: str) -> str:
    """scrape the API version from the HTML and create the reviews API"""
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, **BASE_CONFIG)
    )
    buildId = json.loads(response.selector.xpath("//script[@id='__NEXT_DATA__']/text()").get())["buildId"]
    business_unit = url.split("review/")[-1]

    return f"https://www.trustpilot.com/_next/data/{buildId}/review/{business_unit}.json?sort=recency&businessUnit={business_unit}"


async def scrape_reviews(url: str, max_pages: int = None) -> List[Dict]:
    """parse review data from the API"""
    # create the reviews API url
    log.info(f"getting the reviews API for the URL {url}")
    api_url = await get_reviews_api_url(url)
    # send a POST request to the first review page and get the result directly in JSON
    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(api_url, method="POST", **BASE_CONFIG)
    )
    data = json.loads(first_page.scrape_result["content"])["pageProps"]
    reviews_data = data["reviews"]

    # get the number of review pages to scrape
    total_pages = data["filters"]["pagination"]["totalPages"]
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    log.info(f"scraping reviews pagination ({total_pages - 1} more pages)")
    # add the remaining search pages in a scraping list
    other_pages = [
        ScrapeConfig(api_url + f"&page={page_number}", method="POST", **BASE_CONFIG)
        for page_number in range(2, total_pages + 1)
    ]
    # scrape the remaining search pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        data = json.loads(response.scrape_result["content"])["pageProps"]["reviews"]
        reviews_data.extend(data)
    log.success(f"scraped {len(reviews_data)} company reviews")
    return reviews_data
