"""
This is an example web scraper for expedia.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional, TypedDict
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


class Flight(TypedDict):
    origin: str
    destination: str
    airline: Optional[str]
    price: Optional[str]
    departure_time: Optional[str]
    arrival_time: Optional[str]
    duration: Optional[str]
    stops: Optional[str]
    cabin_class: str
    captured_at: str


def build_hotel_search_url(destination: str, check_in: str, check_out: str, adults: int = 2) -> str:
    return "https://www.expedia.com/Hotel-Search?" + urlencode({
        "destination": destination,
        "startDate": check_in,
        "endDate": check_out,
        "adults": adults,
    })


def build_flight_search_url(
    origin: str, destination: str, departure_date: str, return_date: Optional[str] = None, adults: int = 1
) -> str:
    origin, destination = origin.upper(), destination.upper()
    departure = datetime.strptime(departure_date, "%Y-%m-%d").strftime("%m/%d/%Y")
    params = {
        "leg1": f"from:{origin},to:{destination},departure:{departure}TANYT",
        "passengers": f"adults:{adults}",
        "trip": "oneway",
        "mode": "search",
    }
    if return_date:
        arrival = datetime.strptime(return_date, "%Y-%m-%d").strftime("%m/%d/%Y")
        params["leg2"] = f"from:{destination},to:{origin},departure:{arrival}TANYT"
        params["trip"] = "roundtrip"
    return "https://www.expedia.com/Flights-Search?" + urlencode(params, safe=":,")


def _find_graphql_call(xhr_calls: List[Dict], query_name: str) -> Dict:
    """find a GraphQL XHR call by query name in captured search-page traffic"""
    for call in xhr_calls:
        if GRAPHQL_URL in call["url"] and query_name in (call.get("body") or ""):
            return call
    raise ValueError(f"could not find {query_name} call in captured browser traffic")


def build_next_page_config(
    captured_call: Dict,
    session: str,
    next_start_index: int,
    page_size: int,
    search_type: Literal["hotel", "flight"] = "hotel",
) -> ScrapeConfig:
    """build ScrapeConfig for the next GraphQL page reusing session and captured headers"""
    payload = json.loads(captured_call["body"])
    if search_type == "hotel":
        for count in payload["variables"]["criteria"]["secondary"]["counts"]:
            if count["id"] == "resultsStartingIndex":
                count["value"] = next_start_index
            elif count["id"] == "resultsSize":
                count["value"] = page_size
    else:
        payload[0]["variables"]["searchPagination"] = {"size": page_size, "startingIndex": next_start_index}
    return ScrapeConfig(
        GRAPHQL_URL,
        method="POST",
        body=json.dumps(payload),
        headers=captured_call["headers"],
        session=session,
        **{**BASE_CONFIG, "render_js": False},
    )


def _has_next_page(page_data: Dict | List[Dict], search_type: Literal["hotel", "flight"] = "hotel") -> bool:
    """check whether the server indicates more results are available"""
    if search_type == "hotel":
        pagination = page_data["data"]["propertySearch"].get("pagination") or {}
        return bool((pagination.get("subSets") or {}).get("nextSubSet"))
    return bool(page_data[0]["data"]["flightsSearch"]["listingResult"].get("moreListingsAvailable"))


def parse_hotels(page_data: Dict, captured_at: str) -> List[Hotel]:
    """parse LodgingCard listings from a PropertyListingQuery response"""
    search = page_data["data"]["propertySearch"]
    region = search.get("criteria", {}).get("primary", {}).get("destination", {}).get("regionName", "")
    market_country = region.rsplit(", ", 1)[-1] if region else None

    analytics = (page_data.get("extensions") or {}).get("analytics") or [{}]
    hotel_results = (
        analytics[0].get("tealiumUtagData", {}).get("entity", {}).get("hotels", {}).get("results", {}).get("results") or []
    )
    star_ratings = {
        str(item["hotelId"]): item.get("starRating")
        for item in hotel_results
        if isinstance(item, dict) and "hotelId" in item
    }

    hotels = []
    for listing in search.get("propertySearchListings", []):
        if listing.get("__typename") != "LodgingCard":
            continue

        hotel_id = listing.get("id")
        heading = listing.get("headingSection") or {}
        summary = (listing.get("summarySections") or [{}])[0] or {}
        review = summary.get("reviewSummary") or {}
        review_text = (review.get("graphic") or {}).get("text")
        subtexts = review.get("subtexts") or [{}]
        review_count_text = ((subtexts[0] or {}).get("shoppingProductTitle") or {}).get("text", "")

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

        messages = heading.get("messages") or [{}]
        hotels.append({
            "hotel_id": hotel_id,
            "name": heading.get("heading"),
            "url": ((listing.get("cardLink") or {}).get("resource") or {}).get("value"),
            "nightly_price": nightly_price,
            "total_price": total_price,
            "star_rating": star_ratings.get(hotel_id),
            "review_score": float(review_text) if review_text else None,
            "review_count": int(re.sub(r"\D", "", review_count_text)) if review_count_text else None,
            "location": (messages[0] or {}).get("text"),
            "market_country": market_country,
            "captured_at": captured_at,
        })
    return hotels


def parse_flights(page_data: List[Dict], origin: str, destination: str, cabin_class: str, captured_at: str) -> List[Flight]:
    """parse FlightsStandardOffer listings from a FlightsSearchResultsLoadedQuery response"""
    listing_result = page_data[0]["data"]["flightsSearch"]["listingResult"]

    flights = []
    for listing in listing_result.get("listings", []):
        if listing.get("__typename") != "FlightsStandardOffer":
            continue

        content = listing.get("flightsShoppingOfferContent") or {}
        secondary = content.get("secondarySection") or []
        timeline = (secondary[0] or {}) if secondary else {}
        stops_count = timeline.get("stops")
        if stops_count is None:
            stops = None
        elif stops_count == 0:
            stops = "Nonstop"
        else:
            stops = f"{stops_count} stop" + ("s" if stops_count > 1 else "")

        airline_contents = ((secondary[1] or {}).get("contents") or []) if len(secondary) > 1 else []
        airline = airline_contents[-1].get("text") if airline_contents else None

        tertiary = content.get("tertiarySection") or []
        duration_contents = ((tertiary[0] or {}).get("contents") or []) if tertiary else []
        duration_text = duration_contents[0].get("text") if duration_contents else None
        duration = duration_text.split(" • ")[0] if duration_text else None

        price = None
        for row in (listing.get("priceDisplay") or {}).get("rows") or []:
            for element in row.get("elements") or []:
                price_text = (element.get("price") or {}).get("text")
                if price_text:
                    price = price_text

        flights.append({
            "origin": origin,
            "destination": destination,
            "airline": airline,
            "price": price,
            "departure_time": (timeline.get("start") or {}).get("primary"),
            "arrival_time": (timeline.get("end") or {}).get("primary"),
            "duration": duration,
            "stops": stops,
            "cabin_class": cabin_class,
            "captured_at": captured_at,
        })
    return flights


async def scrape_hotel_search(
    destination: str, check_in: str, check_out: str, adults: int = 2, max_pages: int = 3
) -> List[Hotel]:
    session = f"expedia-{uuid.uuid4().hex}"
    captured_at = datetime.now(timezone.utc).isoformat()

    search_response = await SCRAPFLY.async_scrape(ScrapeConfig(
        url=build_hotel_search_url(destination, check_in, check_out, adults),
        session=session,
        wait_for_selector="xhr:graphql",
        rendering_wait="5000",
        auto_scroll=True,
        **BASE_CONFIG,
    ))
    captured_call = _find_graphql_call(
        search_response.scrape_result["browser_data"]["xhr_call"], "PropertyListingQuery"
    )

    page_data = json.loads(captured_call["response"]["body"])
    hotels = parse_hotels(page_data, captured_at)

    page = 1
    next_start_index = PAGE_SIZE
    while _has_next_page(page_data, "hotel") and page < max_pages:
        response = await SCRAPFLY.async_scrape(build_next_page_config(
            captured_call, session, next_start_index, PAGE_SIZE, "hotel"
        ))
        page_data = json.loads(response.content)
        hotels.extend(parse_hotels(page_data, captured_at))
        page += 1
        log.info(f"expedia: fetched page {page}/{max_pages} (startingIndex={next_start_index})")
        next_start_index += PAGE_SIZE

    return hotels


async def scrape_flight_search(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    cabin_class: str = "economy",
    max_pages: int = 3,
) -> List[Flight]:
    session = f"expedia-{uuid.uuid4().hex}"
    captured_at = datetime.now(timezone.utc).isoformat()
    origin, destination = origin.upper(), destination.upper()

    search_response = await SCRAPFLY.async_scrape(ScrapeConfig(
        url=build_flight_search_url(origin, destination, departure_date, return_date, adults),
        session=session,
        auto_scroll=True,
        wait_for_selector="xhr:graphql",
        rendering_wait="5000",
        **BASE_CONFIG,
    ))
    captured_call = _find_graphql_call(
        search_response.scrape_result["browser_data"]["xhr_call"], "FlightsSearchResultsLoadedQuery"
    )

    page_data = json.loads(captured_call["response"]["body"])
    flights = parse_flights(page_data, origin, destination, cabin_class, captured_at)

    page = 1
    next_start_index = len(flights)
    while _has_next_page(page_data, "flight") and page < max_pages:
        response = await SCRAPFLY.async_scrape(build_next_page_config(
            captured_call, session, next_start_index, PAGE_SIZE, "flight"
        ))
        page_data = json.loads(response.content)
        flights.extend(parse_flights(page_data, origin, destination, cabin_class, captured_at))
        page += 1
        log.info(f"expedia: fetched flight page {page}/{max_pages} (startingIndex={next_start_index})")
        next_start_index += PAGE_SIZE

    return flights
