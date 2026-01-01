"""
This is an example web scraper for Ticketmaster.com using Scrapfly
https://scrapfly.io/blog/posts/how-to-scrape-ticketmaster

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard
"""

import os
import json
import re
import urllib.parse
from pathlib import Path
from loguru import logger as log
from typing import List, Dict, TypedDict, Optional
from scrapfly import (
    ScrapeConfig,
    ScrapflyClient,
    ScrapeApiResponse,
    ScrapflyScrapeError,
)


SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Ticketmaster.com requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "render_js": True,
    "retry": True,
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


class TicketmasterEvent(TypedDict):
    """Ticketmaster event data structure"""
    event_name: str
    event_url: str
    date: str
    time: Optional[str]
    venue_name: str
    venue_location: str
    ticket_url: str


class TicketmasterArtist(TypedDict):
    """Ticketmaster artist page data structure"""
    artist_name: str
    artist_url: str
    genre: Optional[str]
    events_count: int
    events: List[TicketmasterEvent]


class TicketmasterSearch(TypedDict):
    """Ticketmaster search/discovery results"""
    events: List[Dict]
    scraped_pages: int
    events_count: int
    total_pages: int
    total_count: int


def parse_artist_page(result: ScrapeApiResponse) -> TicketmasterArtist:
    """Parse Ticketmaster artist page for artist and event data"""
    sel = result.selector

    # Extract artist name (h1 tag)
    artist_name = sel.xpath('//h1/text()').get("") or ""
    
    # Extract genre - selector from blog post: #main-content > div:nth-child(1) > div:nth-child(2) > div > div > div > p
    genre = sel.xpath('//*[@id="main-content"]/div[1]/div[2]/div/div/div/p/text()').get("") or None
    if genre:
        genre = genre.strip()
    
    # Extract events from the page
    events = []
    # TODO: Implement actual parsing logic based on Ticketmaster's HTML structure
    # Look for event listings in the page and extract:
    # - event_name
    # - event_url
    # - date
    # - time
    # - venue_name
    # - venue_location
    # - ticket_url
    
    parsed_data = {
        "artist_name": artist_name,
        "artist_url": result.context.get("url", ""),
        "genre": genre,
        "events_count": len(events),
        "events": events,
    }

    return parsed_data


async def scrape_artist(urls: list[str]) -> List[TicketmasterArtist]:
    """Scrape Ticketmaster artist pages for artist and event data"""
    log.info(f"Scraping {len(urls)} artist pages")
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    data = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        # Check if this is a successful response or an error
        if isinstance(response, ScrapflyScrapeError):
            log.error(f"Error scraping artist: {response.error}")
            continue
        if not isinstance(response, ScrapeApiResponse):
            log.error(f"Unexpected response type: {type(response)}")
            continue
        try:
            data.append(parse_artist_page(response))
        except Exception as e:
            url = response.context.get("url", "unknown") if hasattr(response, "context") else "unknown"
            log.error(f"Error parsing artist page {url}: {e}")
            continue
    log.success(f"Scraped {len(data)} artist pages")
    return data


def parse_search(result: ScrapeApiResponse) -> TicketmasterSearch:
    """Parse Ticketmaster search/discovery page for event listings"""
    sel = result.selector
    
    # TODO: Implement actual parsing logic based on Ticketmaster's search page structure
    # Extract pagination info and event listings
    
    events = []
    total_pages = 1
    total_count = 0

    log.info(f"Parsed {len(events)} events from search page")
    data = {
        "events": events,
        "scraped_pages": 1,
        "events_count": len(events),
        "total_pages": total_pages,
        "total_count": total_count,
    }
    return data


async def scrape_search(query: str, max_pages: int = 3, scrape_all_pages: bool = False) -> TicketmasterSearch:
    """
    Scrape Ticketmaster search/discovery pages for event listings
    Args:
        query: Search query string
        max_pages: Maximum number of pages to scrape (default: 3)
        scrape_all_pages: If True, scrape all available pages (overrides max_pages)
    """
    encoded_query = urllib.parse.quote(query)
    base_url = f"https://www.ticketmaster.com/discovery/v2/events.json?keyword={encoded_query}"
    log.info(f"Scraping base url {base_url}")
    
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(base_url, **BASE_CONFIG))

    # Check if first page is an error
    if isinstance(first_page, ScrapflyScrapeError):
        log.error(f"Error scraping first page: {first_page.error}")
        return {
            "events": [],
            "scraped_pages": 0,
            "events_count": 0,
            "total_pages": 0,
            "total_count": 0,
        }
    if not isinstance(first_page, ScrapeApiResponse):
        log.error(f"Unexpected response type: {type(first_page)}")
        return {
            "events": [],
            "scraped_pages": 0,
            "events_count": 0,
            "total_pages": 0,
            "total_count": 0,
        }

    # Parse first page
    first_page_data = parse_search(first_page)
    search_results = first_page_data["events"]
    total_pages = first_page_data["total_pages"]
    log.info(f"Found {total_pages} total pages with {first_page_data['total_count']} total events")

    if scrape_all_pages:
        pages_to_scrape = total_pages
    else:
        pages_to_scrape = min(max_pages, total_pages)

    log.info(f"Scraping {pages_to_scrape - 1} additional pages (total: {pages_to_scrape})")
    scraped_pages = 1
    if pages_to_scrape > 1:
        other_pages = [
            ScrapeConfig(f"{base_url}&page={page}", **BASE_CONFIG)
            for page in range(2, pages_to_scrape + 1)
        ]

        log.info(f"Scraping {len(other_pages)} additional pages")
        async for result in SCRAPFLY.concurrent_scrape(other_pages):
            if isinstance(result, ScrapflyScrapeError):
                log.error("ASP protection failed - skipping page")
                continue
            if not isinstance(result, ScrapeApiResponse):
                log.error(f"Unexpected response type: {type(result)}")
                continue
            try:
                page_data = parse_search(result)
                search_results.extend(page_data["events"])
                scraped_pages += 1
            except Exception as e:
                log.error(f"Error parsing search page: {e}")
                continue
        log.success(f"Scraped {len(search_results)} total events from {scraped_pages} pages")
    
    data = {
        "events": search_results,
        "scraped_pages": scraped_pages,
        "events_count": len(search_results),
        "total_pages": total_pages,
        "total_count": first_page_data["total_count"],
    }
    return data

