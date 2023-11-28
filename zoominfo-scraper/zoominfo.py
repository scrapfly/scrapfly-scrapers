"""
This is an example web scraper for zoominfo.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
from typing import Dict, List
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass zoominfo.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
}


def _unescape_angular(text):
    """Helper function to unescape Angular quoted text"""
    ANGULAR_ESCAPE = {
        "&a;": "&",
        "&q;": '"',
        "&s;": "'",
        "&l;": "<",
        "&g;": ">",
    }
    for from_, to in ANGULAR_ESCAPE.items():
        text = text.replace(from_, to)
    return text


def parse_company(response: ScrapeApiResponse) -> List[Dict]:
    """parse zoominfo company page for company data"""
    selector = response.selector
    data = selector.css("script#app-root-state::text").get()
    data = _unescape_angular(data)
    data = json.loads(data)["cd-pageData"]
    return data


def parse_directory(response: ScrapeApiResponse) -> dict:
    """parse zoominfo directory pages"""
    selector = response.selector
    companies = selector.css("div.tableRow_companyName_nameAndLink>a::attr(href)").getall()
    pagination = selector.css("div.pagination>a::attr(href)").getall()
    return {"companies": companies, "pagination": pagination}


async def scrape_comapnies(urls: List[str]) -> List[Dict]:
    """scrape company data from zoominfo company pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    companies = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        companies.append(parse_company(response))
    log.success(f"scraped {len(companies)} company pages data")
    return companies


async def scrape_directory(url: str, scrape_pagination=True) -> List[str]:
    """scrape zoominfo directory pages for company page URLs"""
    # parse first page of the results
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_directory(response)
    companies = data["companies"]
    pagination = data["pagination"]
    # parse other pages of the results
    if scrape_pagination:
        for page_url in pagination:
            companies.extend(await scrape_directory("https://www.zoominfo.com" + page_url, scrape_pagination=False))
    log.success(f"scraped {len(companies)} company page URLs from directory pages")
    return companies
