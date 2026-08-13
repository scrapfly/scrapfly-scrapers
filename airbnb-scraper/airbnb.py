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


def _parse_search_payloads(response: ScrapeApiResponse) -> List[Dict]:
    """extract the staysSearch result payloads embedded in a search page"""
    match = re.search(r'id="data-deferred-state-0"[^>]*>(.*?)</script>', response.content, re.DOTALL)
    if not match:
        return []

    niobe = json.loads(match.group(1).strip()).get("niobeClientData", [])
    payloads = []
    for entry in niobe:
        if not isinstance(entry, list) or len(entry) < 2:
            continue
        if not entry[0].startswith("StaysSearch:"):
            continue
        payloads.append(entry[1]["data"]["presentation"]["staysSearch"]["results"])
    return payloads


def parse_total_pages(response: ScrapeApiResponse) -> int:
    """parse the number of available search pages

    taken from the embedded JSON rather than the pagination nav, which isn't
    always rendered by the time the page is captured
    """
    for payload in _parse_search_payloads(response):
        cursors = (payload.get("paginationInfo") or {}).get("pageCursors") or []
        if cursors:
            return len(cursors)
    return 1


def parse_search(response: ScrapeApiResponse) -> List[AirbnbSearchResult]:
    """parse search results from an Airbnb search page"""
    results = []

    for payload in _parse_search_payloads(response):
        for item in payload["searchResults"]:
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
    location = None
    price_per_night = None
    price_total = None
    rating = None
    review_count = None

    xhr_calls = response.scrape_result.get("browser_data", {}).get("xhr_call", [])
    section_list = list(sections["sections"])
    for call in xhr_calls:
        if "StaysPdpSections" not in call.get("url", ""):
            continue
        try:
            body = json.loads(call["response"]["body"])
        except (KeyError, TypeError, ValueError):
            continue
        hydrated = (((body.get("data") or {}).get("presentation") or {}).get("stayProductDetailPage") or {}).get("sections") or {}
        section_list.extend(hydrated.get("sections") or [])

    for section in section_list:
        kind = section["sectionComponentType"]
        data = section.get("section") or {}

        if kind == "MEET_YOUR_HOST":
            card = data.get("cardData")  # older payloads; newer ones ship an empty stub here
            if card:
                host = {"name": card["name"], "is_superhost": card["isSuperhost"]}
        elif kind == "LOCATION_PDP":
            # older payloads inline the location here; newer ones ship an empty stub
            if data.get("lat") is not None:
                coordinates = {"lat": data["lat"], "lng": data["lng"]}
            location = location or data.get("subtitle")
        elif kind == "BOOK_IT_SIDEBAR":
            display_price = data.get("structuredDisplayPrice") or {}
            line = display_price.get("primaryLine") or {}
            # per-night lines carry "price"; discounted total lines carry "discountedPrice"
            price = line.get("price") or line.get("discountedPrice")
            qualifier = line.get("qualifier") or ""
            if price:
                price_total = f"{price} {qualifier}".strip()
                if re.fullmatch(r"(per\s+)?night", qualifier.strip(), re.IGNORECASE):
                    price_per_night = price
            if not price_per_night:
                # nightly rate only appears in the breakdown, e.g. "7 nights x $203.44"
                for group in (display_price.get("explanationData") or {}).get("priceDetails") or []:
                    for item in group.get("items") or []:
                        m = re.search(r"nights?\s*x\s*(\$[\d,.]+)", item.get("description") or "")
                        if m:
                            price_per_night = m.group(1)
                            break
        elif kind == "REVIEWS_DEFAULT":
            rating = data.get("overallRating")
            review_count = data.get("overallCount")

    pdp_location = pdp.get("location") or {}
    if coordinates is None and pdp_location.get("latitude") is not None:
        coordinates = {"lat": pdp_location["latitude"], "lng": pdp_location["longitude"]}
    location = location or pdp_location.get("subtitle")

    if host is None:
        passport = (pdp.get("hostInfo") or {}).get("passportData") or {}
        if passport:
            host = {"name": passport.get("name"), "is_superhost": passport.get("isSuperhost")}

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
            limit = min(max_pages, parse_total_pages(response))
            log.info(f"scraping up to {limit} pages")

        results.extend(page_results)
        log.success(f"page {page}: scraped {len(page_results)} listings (total: {len(results)})")

        if page >= limit:
            break

    return results


async def scrape_properties(
    urls: List[str],
    check_in: Optional[str] = None,
    check_out: Optional[str] = None,
    adults: int = 1,
) -> List[AirbnbProperty]:
    """scrape Airbnb property pages

    check_in/check_out (YYYY-MM-DD) are required for price fields
    without stay dates Airbnb returns no pricing data
    """
    results = []
    for url in urls:
        params = {"adults": str(adults)}
        if check_in:
            params["check_in"] = check_in
        if check_out:
            params["check_out"] = check_out
        full_url = url + ("&" if "?" in url else "?") + urlencode(params)
        log.info(f"scraping property page: {full_url}")
        response = await SCRAPFLY.async_scrape(ScrapeConfig(full_url, wait_for_selector="xhr:StaysPdpReviewsQuery", **BASE_CONFIG))
        results.append(parse_property(response))
    return results
