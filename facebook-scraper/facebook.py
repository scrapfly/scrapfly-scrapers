"""
This is an example web scraper for Facebook.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
from typing import Dict, List
from urllib.parse import quote
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass facebook.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
    "render_js": True,
}


def parse_marketplace_listing(response: ScrapeApiResponse) -> Dict:
    """parse marketplace listing data from HTML"""
    pass


async def scrape_marketplace_listings(location: str = "New York, NY", max_items: int = 20) -> List[Dict]:
    """
    Scrape Facebook Marketplace listings for a specific location
    
    Args:
        location: Location to search for marketplace items (e.g., "New York, NY")
        max_items: Maximum number of items to scrape
    
    Returns:
        List of marketplace listing dictionaries
    """
    log.info(f"scraping Facebook Marketplace listings for location: {location}")
    
    # Build marketplace URL with location
    url = f"https://www.facebook.com/marketplace/{quote(location)}"
    
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=url,
            **BASE_CONFIG,
            wait_for_selector="[data-testid='marketplace-listing-card']",
            rendering_wait=5000,
        )
    )
    
    # Parse marketplace listings from the response
    listings = parse_marketplace_listing(result)
    
    log.success(f"scraped {len(listings)} marketplace listings from {location}")
    return listings


def parse_event(response: ScrapeApiResponse) -> Dict:
    """parse event data from HTML"""
    pass


async def scrape_facebook_events(location: str = "New York, NY", max_events: int = 20) -> List[Dict]:
    """
    Scrape Facebook Events for a specific location
    
    Args:
        location: Location to search for events (e.g., "New York, NY")
        max_events: Maximum number of events to scrape
    
    Returns:
        List of event dictionaries
    """
    log.info(f"scraping Facebook Events for location: {location}")
    
    # Build events URL with location
    url = f"https://www.facebook.com/events/search/?q={quote(location)}"
    
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=url,
            **BASE_CONFIG,
            wait_for_selector="[data-testid='event-card']",
            rendering_wait=5000,
        )
    )
    
    # Parse events from the response
    events = parse_event(result)
    
    log.success(f"scraped {len(events)} events from {location}")
    return events

