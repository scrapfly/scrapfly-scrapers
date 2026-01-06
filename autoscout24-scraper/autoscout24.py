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


class CarListing(TypedDict):
    """Car listing from search results"""

    title: str
    price: str
    mileage: Optional[str]
    year: Optional[str]
    fuel_type: Optional[str]
    transmission: Optional[str]
    power: Optional[str]
    location: Optional[str]
    url: str


class CarDetails(TypedDict):
    """Detailed car information from individual car page"""

    title: str
    price: str
    mileage: Optional[str]
    year: Optional[str]
    fuel_type: Optional[str]
    transmission: Optional[str]
    power: Optional[str]
    color: Optional[str]
    body_type: Optional[str]
    doors: Optional[str]
    seats: Optional[str]
    co2_emission: Optional[str]
    features: List[str]
    seller: Dict[str, Any]
    url: str


def parse_listings(result: ScrapeApiResponse) -> List[CarListing]:
    """Parse AutoScout24 listings page for car listings"""
    pass


def parse_car_details(result: ScrapeApiResponse) -> CarDetails:
    """Parse individual car detail page"""
    pass


async def scrape_listings(url: str, max_pages: int = 3) -> List[CarListing]:
    """
    Scrape car listings from AutoScout24 search/category page

    Args:
        url: AutoScout24 listings URL (e.g., https://www.autoscout24.com/lst/c/compact)
        max_pages: Maximum number of pages to scrape

    Returns:
        List of car listings
    """
    pass


async def scrape_car_details(url: str) -> CarDetails:
    """
    Scrape detailed car information from individual car page

    Args:
        url: AutoScout24 car detail URL

    Returns:
        Car details dictionary
    """
    pass



