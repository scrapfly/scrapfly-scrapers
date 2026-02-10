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


JS = [
    {"wait_for_selector": {"selector": "div[aria-label='Close']", "timeout": 3000}},
    {"click": {"selector": "div[aria-label='Close']"}},
    {"wait": 500},
    {"scroll": {"selector": "bottom"}},
]
BASE_CONFIG = {
    # bypass facebook.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
    "render_js": True,
    "js_scenario": JS,
}


def parse_marketplace_listing(response: ScrapeApiResponse) -> List[Dict]:
    """parse marketplace listing data from HTML by extracting JSON from script tags"""
    import re

    def find_listings(obj, depth=0):
        """Recursively find all marketplace listing objects"""
        if depth > 50:
            return []
        if isinstance(obj, dict):
            results = [obj] if obj.get("__typename") in ["GroupCommerceProductItem", "MarketplaceProductItem"] else []
            return results + [item for value in obj.values() for item in find_listings(value, depth + 1)]
        return [
            item for sublist in (obj if isinstance(obj, list) else []) for item in find_listings(sublist, depth + 1)
        ]

    scripts = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', response.content, re.DOTALL)
    all_listings = []
    for script in scripts:
        try:
            all_listings.extend(find_listings(json.loads(script)))
        except (json.JSONDecodeError, Exception):
            continue

    parsed_listings = []
    for listing in all_listings:
        geocode = listing.get("location", {}).get("reverse_geocode", {})
        city, state = geocode.get("city", ""), geocode.get("state", "")
        location = f"{city}, {state}" if city and state else (city or state)

        parsed_listing = {
            "id": listing.get("id"),
            "title": listing.get("marketplace_listing_title"),
            "price": listing.get("formatted_price", {}).get("text", "N/A"),
            "location": location,
            "is_sold": listing.get("is_sold", False),
            "is_pending": listing.get("is_pending", False),
            "creation_time": listing.get("creation_time"),
        }

        if seller_data := listing.get("marketplace_listing_seller"):
            parsed_listing["seller"] = {"name": seller_data.get("name"), "id": seller_data.get("id")}
        if image := listing.get("primary_listing_photo", {}).get("image"):
            parsed_listing["image_url"] = image.get("uri")
        if delivery_types := listing.get("delivery_types"):
            parsed_listing["delivery_types"] = delivery_types
        if category_id := listing.get("marketplace_listing_category_id"):
            parsed_listing["category_id"] = category_id

        parsed_listings.append(parsed_listing)

    log.success(f"parsed {len(parsed_listings)} marketplace listings from the page")
    return parsed_listings


def parse_event(response: ScrapeApiResponse) -> List[Dict]:
    """parse event data from HTML by extracting JSON from script tags"""
    import re

    def find_events(obj):
        """Recursively find all Event objects"""
        if isinstance(obj, dict):
            results = [obj] if obj.get("__typename") == "Event" else []
            return results + [item for value in obj.values() for item in find_events(value)]
        return [item for sublist in (obj if isinstance(obj, list) else []) for item in find_events(sublist)]

    scripts = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', response.content, re.DOTALL)
    all_events = []
    for script in scripts:
        try:
            all_events.extend(find_events(json.loads(script)))
        except (json.JSONDecodeError, Exception):
            continue

    parsed_events = []
    for event in all_events:
        event_place = event.get("event_place", {})
        location = (
            event_place.get("contextual_name", "")
            if event_place
            else ("Online Event" if event.get("is_online") else "")
        )

        parsed_event = {
            "id": event.get("id"),
            "title": event.get("name"),
            "date": event.get("day_time_sentence"),
            "location": location,
            "url": event.get("url") or event.get("eventUrl"),
            "start_timestamp": event.get("start_timestamp"),
            "is_online": event.get("is_online", False),
            "event_kind": event.get("event_kind"),
            "is_past": event.get("is_past", False),
            "is_happening_now": event.get("is_happening_now", False),
            "is_hosted_by_ticket_master": event.get("is_hosted_by_ticket_master", False),
        }

        if event_place:
            parsed_event["location_details"] = {"name": event_place.get("contextual_name"), "id": event_place.get("id")}
        if photo := event.get("cover_photo", {}).get("photo"):
            parsed_event["cover_photo"] = {
                "url": photo.get("eventImage", {}).get("uri"),
                "accessibility_caption": photo.get("accessibility_caption"),
                "id": photo.get("id"),
            }
        if social_context := event.get("social_context"):
            parsed_event["social_context"] = social_context.get("text")
        if price_range := event.get("ticketing_context_row", {}).get("price_range_text"):
            parsed_event["price_range"] = price_range

        parsed_events.append(parsed_event)

    log.success(f"parsed {len(parsed_events)} events from the page")
    return parsed_events


async def scrape_facebook_events(event_name: str = "New York, NY") -> List[Dict]:
    log.info(f"scraping Facebook Events for event: {event_name}")

    # Build events URL with location
    url = f"https://www.facebook.com/events/search?q={quote(event_name)}"
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=url,
            **BASE_CONFIG,
        )
    )

    # Parse events from the response
    events = parse_event(result)

    log.success(f"scraped {len(events)} events from {event_name}")
    return events


async def scrape_marketplace_listings(query: str = "electronics") -> List[Dict]:
    """
    Scrape Facebook Marketplace listings for a specific query

    Args:
        query: Query to search for marketplace items (e.g., "electronics")

    Returns:
        List of marketplace listing dictionaries
    """
    log.info(f"scraping Facebook Marketplace listings for query: {query}")

    # Build marketplace URL with location
    url = f"https://www.facebook.com/marketplace/search/?query={quote(query)}"
    print(url)
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=url,
            **BASE_CONFIG,
        )
    )

    # Parse marketplace listings from the response
    listings = parse_marketplace_listing(result)

    log.success(f"scraped {len(listings)} marketplace listings from {query}")
    return listings
