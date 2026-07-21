"""
This is an example web scraper for expedia.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, TypedDict
from urllib.parse import urlencode
import uuid

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "render_js": True,
    "proxy_pool": "public_residential_pool",
}

GRAPHQL_URL = "https://www.expedia.com/graphql"
PAGE_SIZE = 100

class Hotel(TypedDict):
    hotel_id: Optional[str]
    name: Optional[str]
    url: Optional[str]
    nightly_price: Optional[str]
    total_price: Optional[str]
    star_rating: Optional[float]
    review_score: Optional[float]
    review_count: Optional[int]
    location: Optional[str]
    market_country: Optional[str]
    captured_at: str


def build_hotel_search_url(destination: str, check_in: str, check_out: str, adults: int = 2) -> str:
    return "https://www.expedia.com/Hotel-Search?" + urlencode({
        "destination": destination,
        "startDate": check_in,
        "endDate": check_out,
        "adults": adults,
    })


def _find_property_listing_call(xhr_calls: List[Dict]) -> Dict:
    """find the PropertyListingQuery XHR call in captured search-page traffic"""
    for call in xhr_calls:
        if GRAPHQL_URL in call["url"] and "PropertyListingQuery" in (call.get("body") or ""):
            return call
    raise ValueError("could not find PropertyListingQuery call in captured browser traffic")


def build_next_page_config(
    captured_call: Dict, session: str, next_start_index: int, page_size: int
) -> ScrapeConfig:
    """build ScrapeConfig for the next PropertyListingQuery page reusing session and captured headers"""
    payload = json.loads(captured_call["body"])
    for count in payload["variables"]["criteria"]["secondary"]["counts"]:
        if count["id"] == "resultsStartingIndex":
            count["value"] = next_start_index
        elif count["id"] == "resultsSize":
            count["value"] = page_size
    return ScrapeConfig(
        GRAPHQL_URL,
        method="POST",
        body=json.dumps(payload),
        headers=captured_call["headers"],
        session=session,
        **{**BASE_CONFIG, "render_js": False},
    )


def _next_subset(page_data: Dict) -> Optional[Dict]:
    """read the server-provided next-page cursor (startingIndex/size) off a PropertyListingQuery response, or None if exhausted"""
    pagination = (page_data.get("data") or {}).get("propertySearch", {}).get("pagination")
    if not pagination:
        return None
    return pagination.get("subSets", {}).get("nextSubSet")


def parse_hotels(page_data: Dict, captured_at: str) -> List[Hotel]:
    """parse LodgingCard listings from a PropertyListingQuery response"""
    search = page_data["data"]["propertySearch"]
    region = search.get("criteria", {}).get("primary", {}).get("destination", {}).get("regionName", "")
    market_country = region.rsplit(", ", 1)[-1] if region else None

    analytics = (page_data.get("extensions") or {}).get("analytics") or []
    star_ratings = {
        str(item["hotelId"]): item.get("starRating")
        for item in analytics[0].get("tealiumUtagData", {}).get("entity", {}).get("hotels", {}).get("results", {}).get("results", [])
    } if analytics else {}

    hotels = []
    for listing in search.get("propertySearchListings", []):
        if listing.get("__typename") != "LodgingCard":
            continue

        hotel_id = listing.get("id")
        heading = listing.get("headingSection") or {}
        review = ((listing.get("summarySections") or [{}])[0].get("reviewSummary") or {})
        review_text = review.get("graphic", {}).get("text")
        review_count_text = ((review.get("subtexts") or [{}])[0].get("shoppingProductTitle") or {}).get("text", "")

        nightly_price = total_price = None
        for message in (listing.get("priceSection") or {}).get("priceSummary", {}).get("displayMessages") or []:
            for item in message.get("lineItems") or []:
                value = item.get("value") or (item.get("price") or {}).get("formatted")
                if not value:
                    continue
                if "nightly" in value.lower():
                    nightly_price = value
                elif "$" in value:
                    total_price = value

        hotels.append({
            "hotel_id": hotel_id,
            "name": heading.get("heading"),
            "url": listing.get("cardLink", {}).get("resource", {}).get("value"),
            "nightly_price": nightly_price,
            "total_price": total_price,
            "star_rating": star_ratings.get(hotel_id),
            "review_score": float(review_text) if review_text else None,
            "review_count": int(re.sub(r"\D", "", review_count_text)) if review_count_text else None,
            "location": (heading.get("messages") or [{}])[0].get("text"),
            "market_country": market_country,
            "captured_at": captured_at,
        })
    return hotels


async def scrape_hotel_search(
    destination: str, check_in: str, check_out: str, adults: int = 2, max_pages: int = 3
) -> List[Hotel]:
    session = f"expedia-{uuid.uuid4().hex}"
    captured_at = datetime.now(timezone.utc).isoformat()

    search_response = await SCRAPFLY.async_scrape(ScrapeConfig(
        url=build_hotel_search_url(destination, check_in, check_out, adults),
        session=session,
        auto_scroll=True,
        **BASE_CONFIG,
    ))
    captured_call = _find_property_listing_call(search_response.scrape_result["browser_data"]["xhr_call"])

    page_data = json.loads(captured_call["response"]["body"])
    hotels = parse_hotels(page_data, captured_at)

    next_subset = _next_subset(page_data)
    page = 1
    next_start_index = PAGE_SIZE
    while next_subset and page < max_pages:
        response = await SCRAPFLY.async_scrape(build_next_page_config(
            captured_call, session, next_start_index, PAGE_SIZE
        ))
        page_data = json.loads(response.content)
        hotels.extend(parse_hotels(page_data, captured_at))
        page += 1
        log.info(f"expedia: fetched page {page}/{max_pages} (startingIndex={next_start_index})")
        next_start_index += PAGE_SIZE
        next_subset = _next_subset(page_data)

    return hotels
