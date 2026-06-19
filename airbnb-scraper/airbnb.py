"""
This is an example web scraper for airbnb.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import re
import json
import base64
from urllib.parse import urlencode, quote
from typing import Dict, List, Optional, TypedDict
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "proxy_pool": "public_residential_pool",
    "render_js": True,
    "rendering_wait": 5000,
}


class AirbnbSearchResult(TypedDict):
    id: str
    url: str
    title: Optional[str]
    room_type: Optional[str]
    rating: Optional[float]
    review_count: Optional[int]
    price_total: Optional[str]


class AirbnbProperty(TypedDict):
    url: str
    id: str
    title: Optional[str]
    description: Optional[str]
    room_type: Optional[str]
    overview: Optional[List[str]]
    amenities: Optional[List[str]]
    images: Optional[List[str]]
    host: Optional[Dict]
    coordinates: Optional[Dict]
    location: Optional[str]
    person_capacity: Optional[int]
    rating: Optional[float]
    review_count: Optional[int]
    price_per_night: Optional[str]
    price_total: Optional[str]
    reviews: Optional[List[Dict]]


class AirbnbReview(TypedDict):
    id: str
    reviewer: Optional[str]
    rating: Optional[int]
    date: Optional[str]
    text: Optional[str]
    response: Optional[str]


def _build_search_url(
    query: str,
    check_in: Optional[str] = None,
    check_out: Optional[str] = None,
    adults: int = 1,
    page: int = 1,
) -> str:
    params = {"query": query, "adults": str(adults)}
    if check_in:
        params["checkin"] = check_in
    if check_out:
        params["checkout"] = check_out
    if page > 1:
        params["page"] = str(page)
    slug = quote(query.replace(", ", "-").replace(" ", "-"))
    return f"https://www.airbnb.com/s/{slug}/homes?{urlencode(params)}"


def parse_search(response: ScrapeApiResponse) -> List[AirbnbSearchResult]:
    """parse search results from an Airbnb search page"""
    match = re.search(r'id="data-deferred-state-0"[^>]*>(.*?)</script>', response.content, re.DOTALL)
    if not match:
        return []

    niobe = json.loads(match.group(1).strip()).get("niobeClientData", [])
    results = []

    for entry in niobe:
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        if not entry[0].startswith("StaysSearch:"):
            continue

        listings = entry[1]["data"]["presentation"]["staysSearch"]["results"]["searchResults"]
        for item in listings:
            raw_id = item.get("demandStayListing", {}).get("id", "")
            try:
                listing_id = base64.b64decode(raw_id + "==").decode().split(":")[-1]
            except Exception:
                listing_id = raw_id

            rating = None
            review_count = None
            rating_str = item.get("avgRatingLocalized") or ""
            m = re.match(r"([\d.]+)\s*\((\d+)\)", rating_str)
            if m:
                rating = float(m.group(1))
                review_count = int(m.group(2))

            price = item.get("structuredDisplayPrice", {}).get("primaryLine", {}).get("accessibilityLabel")
            results.append(
                {
                    "id": listing_id,
                    "url": f"https://www.airbnb.com/rooms/{listing_id}",
                    "title": item.get("title"),
                    "room_type": item.get("subtitle"),
                    "rating": rating,
                    "review_count": review_count,
                    "price_total": price,
                }
            )

    return results


def parse_property(response: ScrapeApiResponse) -> AirbnbProperty:
    """parse property data from an Airbnb listing page"""
    match = re.search(r'id="data-deferred-state-0"[^>]*>(.*?)</script>', response.content, re.DOTALL)
    if not match:
        raise ValueError("data-deferred-state-0 script tag not found")

    niobe = json.loads(match.group(1).strip()).get("niobeClientData", [])
    pdp_data = None
    listing_id = ""

    for entry in niobe:
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        key, val = entry[0], entry[1]
        if not key.startswith("StaysPdpSections"):
            continue
        pdp_data = val
        raw_id = re.search(r'demandStayListingId":"([^"]+)"', key).group(1)
        listing_id = base64.b64decode(raw_id + "==").decode().split(":")[-1]
        break

    if not pdp_data:
        raise ValueError("StaysPdpSections data not found")

    node = pdp_data["data"]["node"]
    pdp = node["pdpPresentation"]
    sections = pdp_data["data"]["presentation"]["stayProductDetailPage"]["sections"]
    sharing = sections["metadata"]["sharingConfig"]

    title = pdp["title"]["content"]["localizedString"]
    description = pdp["descriptions"]["longDescriptionHtml"]["localizedString"]
    overview = pdp["overview"]["items"]
    room_type = sharing["propertyType"]
    location = sharing["location"]
    person_capacity = pdp["personCapacity"]

    amenities = []
    for group in pdp["amenities"]["seeAllAmenitiesGroups"]:
        for amenity in group["amenities"]:
            amenities.append(amenity["title"])

    images = []
    for edge in pdp["heroMedia"]["edges"]:
        images.append(edge["node"]["image"]["uri"])

    host = None
    coordinates = None
    price_per_night = None
    price_total = None
    rating = None
    review_count = None

    for section in sections["sections"]:
        kind = section["sectionComponentType"]
        data = section.get("section") or {}

        if kind == "MEET_YOUR_HOST":
            card = data["cardData"]
            host = {"name": card["name"], "is_superhost": card["isSuperhost"]}
        elif kind == "LOCATION_PDP":
            coordinates = {"lat": data["lat"], "lng": data["lng"]}
            location = data["subtitle"]
        elif kind == "BOOK_IT_SIDEBAR":
            line = (data.get("structuredDisplayPrice") or {}).get("primaryLine") or {}
            price_per_night = line.get("price")
            qualifier = line.get("qualifier")
            if price_per_night and qualifier:
                price_total = f"{price_per_night} {qualifier}"
        elif kind == "REVIEWS_DEFAULT":
            rating = data.get("overallRating")
            review_count = data.get("overallCount")

    rating_stats = pdp.get("quality", {}).get("listingRatingStats", {}).get("overallRatingStats", {})
    rating = rating or rating_stats.get("ratingAverage")
    review_count = review_count or (int(rating_stats.get("ratingCount") or 0) or None)

    reviews = []
    xhr_calls = response.scrape_result.get("browser_data", {}).get("xhr_call", [])
    for call in xhr_calls:
        if "StaysPdpReviewsQuery" not in call.get("url", ""):
            continue
        review_data = json.loads(call["response"]["body"])
        for review in review_data["data"]["presentation"]["stayProductDetailPage"]["reviews"]["reviews"]:
            reviews.append(
                {
                    "id": review["id"],
                    "reviewer": review["reviewer"]["firstName"],
                    "rating": review["rating"],
                    "date": review["localizedDate"],
                    "text": review["comments"],
                    "response": review.get("response"),
                }
            )

    url = response.context.get("url", f"https://www.airbnb.com/rooms/{listing_id}")

    return {
        "url": url,
        "id": listing_id,
        "title": title,
        "description": description,
        "room_type": room_type,
        "overview": overview,
        "amenities": amenities,
        "images": images,
        "host": host,
        "coordinates": coordinates,
        "location": location,
        "person_capacity": person_capacity,
        "rating": rating,
        "review_count": review_count,
        "price_per_night": price_per_night,
        "price_total": price_total,
        "reviews": reviews or None,
    }


async def scrape_listings(
    query: str,
    check_in: Optional[str] = None,
    check_out: Optional[str] = None,
    adults: int = 1,
    max_pages: int = 3,
) -> List[AirbnbSearchResult]:
    """scrape Airbnb search results for a location"""
    results = []
    limit = max_pages

    for page in range(1, max_pages + 1):
        url = _build_search_url(query, check_in, check_out, adults, page)
        log.info(f"scraping search page {page}: {url}")
        response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
        page_results = parse_search(response)

        if not page_results:
            log.warning(f"no results on page {page}, stopping")
            break

        if page == 1:
            nav = re.search(r'aria-label="Search results pagination".*?</nav>', response.content, re.DOTALL)
            pages = [int(n) for n in re.findall(r">(\d+)</(?:button|a)>", nav.group(0))] if nav else []
            limit = min(max_pages, max(pages) if pages else 1)
            log.info(f"scraping up to {limit} pages")

        results.extend(page_results)
        log.success(f"page {page}: scraped {len(page_results)} listings (total: {len(results)})")

        if page >= limit:
            break

    return results


async def scrape_properties(urls: List[str]) -> List[AirbnbProperty]:
    """scrape Airbnb property pages"""
    results = []
    for url in urls:
        log.info(f"scraping property page: {url}")
        response = await SCRAPFLY.async_scrape(ScrapeConfig(url, wait_for_selector="xhr:StaysPdpReviewsQuery", **BASE_CONFIG))
        results.append(parse_property(response))
    return results
