"""
This is an example web scraper for AutoScout24.com using Scrapfly
https://scrapfly.io/blog/posts/how-to-scrape-autoscout24

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard
"""
import json
import os
import re
from pathlib import Path
from typing import Dict, List, TypedDict, Optional, Any

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # AutoScout24 requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


class CarListing(TypedDict, total=False):
    """Car listing from search results"""
    price: Dict[str, str]
    url: str
    location: Optional[Dict[str, Optional[str]]]
    vehicle: Optional[Dict[str, Any]]
    tracking: Optional[Dict[str, Any]]
    vehicleDetails: Optional[List[Dict[str, Any]]]


class CarDetails(TypedDict, total=False):
    """Detailed car information from car page"""
    
    price: Dict[str, str]
    vehicle: Optional[Dict[str, Any]]
    seller: Optional[Dict[str, Any]]
    location: Optional[Dict[str, Any]]


def parse_listings(result: ScrapeApiResponse) -> List[CarListing]:
    """Parse AutoScout24 listings page for car listings"""
    selector = result.selector

    script_data = selector.css("script#__NEXT_DATA__::text").get()
    if not script_data:
        log.warning(f"Could not find __NEXT_DATA__ on page: {result.context['url']}")
        return []
    data = json.loads(script_data)
    listings = data.get("props", {}).get("pageProps", {}).get("listings", [])
    
    return listings

def parse_car_details(result: ScrapeApiResponse) -> CarDetails:
    """Parse car detail page"""
    selector = result.selector
    script_data = selector.css("script#__NEXT_DATA__::text").get()
    if not script_data:
        log.warning(f"Could not find __NEXT_DATA__ on page: {result.context['url']}")
        return None
    data = json.loads(script_data)
    car_data = data.get("props", {}).get("pageProps", {}).get("listingDetails", {})

    return car_data


async def scrape_listings(url: str, max_pages: int = 3) -> List[CarListing]:
    """
    Scrape car listings from AutoScout24 search/category page

    Args:
        url: AutoScout24 listings URL (e.g., https://www.autoscout24.com/lst/c/compact
            or https://www.autoscout24.com/lst/bmw/116/bt_compact?&damaged_listing=exclude&desc=0&powertype=kw&search_id=1ws8t0eo2sb&sort=standard ) to suport filtering options
        max_pages: Maximum number of pages to scrape

    Returns:
        List of car listings
    """
    all_listings = []
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    all_listings.extend(parse_listings(result))
    # check if url contains '?' to determine if we should use '&' or '?' for the page parameter
    if "?" in url:
        page_param = "&page="
    else:
        page_param = "?page="
    other_pages = [ScrapeConfig(url + f"{page_param}{page}", **BASE_CONFIG) for page in range(2, max_pages + 1)]
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        log.info(f"Scraping page {response.context['url']}")
        all_listings.extend(parse_listings(response))
    log.info(f"Scraped {len(all_listings)} car listings from {url}")
    return all_listings

async def scrape_car_details(urls: List[str]) -> List[CarDetails]:
    """
    Scrape detailed car information from car page

    Args:
        urls: List of AutoScout24 car detail URLs

    Returns:
        List of car details dictionaries
    """
    all_car_details = []
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        all_car_details.append(parse_car_details(response))
    log.info(f"Scraped {len(all_car_details)} car details from {urls}")
    return all_car_details
