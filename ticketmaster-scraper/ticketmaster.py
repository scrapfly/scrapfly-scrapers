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


class TicketmasterArtist(TypedDict):
    """Ticketmaster artist page data structure"""

    artist_name: str
    ratingValue: Optional[float]
    bestRating: Optional[int]
    ratingCount: Optional[int]
    genre: Optional[str]
    events_count: int
    events: List[Dict]
    reviews: List[Dict]


class TicketmasterSearch(TypedDict):
    """Ticketmaster search/discovery results"""

    events: List[Dict]
    events_count: int
    total_count: int


def extract_balanced_dict(text: str, start_pattern: str) -> Optional[Dict]:
    """
    Extract a balanced JSON dictionary from text starting with a pattern.

    Args:
        text: The text to search in
        start_pattern: Pattern to find (e.g., 'window.digitalData=')

    Returns:
        Parsed dictionary or None if not found
    """
    start_idx = text.find(start_pattern)
    if start_idx == -1:
        return None

    # Find the opening brace after the pattern
    brace_start = text.find("{", start_idx)
    if brace_start == -1:
        return None

    # Count braces to find the matching closing brace
    brace_count = 0
    for i in range(brace_start, len(text)):
        if text[i] == "{":
            brace_count += 1
        elif text[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                # Found the matching closing brace
                json_str = text[brace_start : i + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    return None

    return None


def parse_artist_page(result: ScrapeApiResponse) -> TicketmasterArtist:
    """Parse Ticketmaster artist page for artist and event data"""
    sel = result.selector

    # Extract JSON-LD scripts
    json_ld_scripts = sel.xpath('//script[@type="application/ld+json"]/text()').getall()

    # Find MusicGroup JSON-LD for artist info
    artist_data = None
    events_data = []
    genre = None

    for script_text in json_ld_scripts:
        try:
            data = json.loads(script_text)
            # Handle both single objects and lists
            if isinstance(data, list):
                # Check items in the list
                for item in data:
                    item_type = item.get("@type")
                    if item_type in ["MusicGroup", "TheaterGroup"]:
                        artist_data = item
                    elif item_type in ["MusicEvent", "TheaterEvent"]:
                        events_data.append(item)
            else:
                # Single object
                data_type = data.get("@type")
                if data_type in ["MusicGroup", "TheaterGroup"]:
                    artist_data = data
                elif data_type in ["MusicEvent", "TheaterEvent"]:
                    events_data.append(data)
        except json.JSONDecodeError:
            continue

    # Extract artist name
    artist_name = ""
    if artist_data and artist_data.get("name"):
        artist_name = artist_data.get("name")

    ratingValue = None
    bestRating = None
    ratingCount = None
    if artist_data and artist_data.get("aggregateRating"):
        aggregate_rating = artist_data.get("aggregateRating")
        if isinstance(aggregate_rating, dict):
            ratingValue = aggregate_rating.get("ratingValue")
            bestRating = aggregate_rating.get("bestRating")
            ratingCount = aggregate_rating.get("ratingCount")

    # Extract genre from digitalData script
    digital_data_script = sel.xpath('//script[@id="digitalData"]/text()').get()
    if digital_data_script:
        digital_data = extract_balanced_dict(digital_data_script, "window.digitalData=")
        if digital_data:
            try:
                # Navigate to genre: page.attributes.discovery.attraction[0].classifications.genre.name
                attraction = (
                    digital_data.get("page", {}).get("attributes", {}).get("discovery", {}).get("attraction", [])
                )
                if attraction and len(attraction) > 0:
                    classifications = attraction[0].get("classifications", {})
                    genre_obj = classifications.get("genre", {})
                    genre = genre_obj.get("name") if genre_obj else None
            except (KeyError, IndexError, AttributeError) as e:
                log.debug(f"Error extracting genre from digitalData: {e}")

    # Extract reviews from artist_data
    reviews = []
    if artist_data and artist_data.get("reviews"):
        raw_reviews = artist_data.get("reviews", [])
        for review in raw_reviews:
            parsed_review = {
                "title": review.get("name", ""),
                "description": review.get("description", ""),
                "datePublished": review.get("datePublished", ""),
                "author_name": "",
                "ratingValue": None,
                "bestRating": None,
            }
            # Extract author name
            author = review.get("author", {})
            if isinstance(author, dict):
                parsed_review["author_name"] = author.get("name", "")
            # Extract rating
            review_rating = review.get("reviewRating", {})
            if isinstance(review_rating, dict):
                parsed_review["ratingValue"] = review_rating.get("ratingValue")
                parsed_review["bestRating"] = review_rating.get("bestRating")
            reviews.append(parsed_review)

    parsed_data = {
        "artist_name": artist_name,
        "ratingValue": ratingValue,
        "bestRating": bestRating,
        "ratingCount": ratingCount,
        "genre": genre,
        "events_count": len(events_data),
        "events": events_data,
        "reviews": reviews,
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
        try:
            data.append(parse_artist_page(response))
        except Exception as e:
            url = response.context.get("url", "unknown") if hasattr(response, "context") else "unknown"
            log.error(f"Error parsing artist page {url}: {e}")
            continue
    log.success(f"Scraped {len(data)} artist pages")
    return data


def parse_discovery_response(result: ScrapeApiResponse) -> TicketmasterSearch:
    """Parse Ticketmaster discovery HTML page for event listings from JSON-LD scripts"""
    sel = result.selector

    # Extract JSON-LD scripts
    json_ld_scripts = sel.xpath('//script[@type="application/ld+json"]/text()').getall()

    events = []
    for script_text in json_ld_scripts:
        try:
            data = json.loads(script_text)
            # Handle both array and single object responses
            event_list = data if isinstance(data, list) else [data]

            for event_data in event_list:
                if event_data.get("@type") == "MusicEvent":
                    # Extract event information
                    event_name = event_data.get("name", "")
                    event_url = event_data.get("url", "")

                    # Extract dates
                    start_date = event_data.get("startDate", "")
                    date = start_date.split("T")[0] if start_date else ""
                    time = start_date.split("T")[1] if "T" in start_date else None

                    # Extract venue information
                    location = event_data.get("location", {})
                    venue_name = location.get("name", "") if isinstance(location, dict) else ""
                    address = location.get("address", {}) if isinstance(location, dict) else {}
                    city = address.get("addressLocality", "") if isinstance(address, dict) else ""
                    state = address.get("addressRegion", "") if isinstance(address, dict) else ""
                    venue_location = f"{city}, {state}".strip(", ") if city or state else ""

                    # Extract ticket URL from offers
                    ticket_url = event_url  # Default to event URL
                    offers = event_data.get("offers", {})
                    if isinstance(offers, dict) and offers.get("url"):
                        ticket_url = offers.get("url", event_url)

                    events.append(
                        {
                            "event_name": event_name,
                            "event_url": event_url,
                            "date": date,
                            "time": time,
                            "venue_name": venue_name,
                            "venue_location": venue_location,
                            "ticket_url": ticket_url,
                        }
                    )
        except json.JSONDecodeError:
            continue

    # Extract total count from span with aria-live="polite" (e.g., "152 Results")
    total_count_text = sel.xpath("//span[@aria-live='polite' and contains(@class, 'gOraUu')]/text()").get()
    total_count = len(events)  # Default to parsed events count
    if total_count_text:
        match = re.search(r"(\d+)", total_count_text)
        if match:
            total_count = int(match.group(1))
    events_count = len(events)
    log.info(f"Parsed {events_count} events from discovery page (total: {total_count})")
    return {
        "events": events,
        "events_count": events_count,
        "total_count": total_count,
    }


async def scrape_discovery(base_url: str, **kwargs) -> TicketmasterSearch:
    """
    Scrape Ticketmaster discovery API for event listings
    Args:
        base_url: Base URL for discovery API (e.g., "https://www.ticketmaster.com/discovery/v2/events.json")
        **kwargs: Filter parameters (e.g., classificationId, startDate, endDate, etc.)
    """
    # Build URL with query parameters
    url_parts = list(urllib.parse.urlparse(base_url))
    query_params = dict(urllib.parse.parse_qsl(url_parts[4]))
    query_params.update(kwargs)
    url_parts[4] = urllib.parse.urlencode(query_params)
    url = urllib.parse.urlunparse(url_parts)

    log.info(f"Scraping discovery : {url}")

    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))

    if isinstance(result, ScrapflyScrapeError):
        log.error(f"Error scraping discovery URL: {result.error}")
        return {}

    # Parse the HTML page
    data = parse_discovery_response(result)
    return data
