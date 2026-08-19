"""
This is an example web scraper for goibibo.com hotel search.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"

For example use instructions see ./run.py
"""
import base64
import gzip
import json
import os
import re
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional, TypedDict
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from uuid import uuid4

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "IN",
    "render_js": True,
    "proxy_pool": "public_residential_pool",
    "auto_scroll": True,
}

LISTING_API = "clientbackend-gi/cg/listing/DESKTOP/"
SEARCH_STREAM_DT = "search-stream-dt"


class Hotel(TypedDict):
    id: str
    gi_id: Optional[str]
    name: str
    property_type: Optional[str]
    star_rating: Optional[int]
    sold_out: bool
    total_room_count: Optional[int]
    categories: List[str]
    area: Optional[str]
    city: Optional[str]
    country: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    images: List[str]
    price: Optional[float]
    price_with_tax: Optional[float]
    price_suffix: Optional[str]
    currency: Optional[str]
    rating: Optional[float]
    rating_text: Optional[str]
    review_count: Optional[int]
    rating_count: Optional[int]
    amenities: List[str]
    description: Optional[str]
    url: Optional[str]

class FlightLeg(TypedDict):
    flight_number: Optional[str]
    airline: Optional[str]
    aircraft: Optional[str]
    departure_city: Optional[str]
    departure_time: Optional[str]
    arrival_city: Optional[str]
    arrival_time: Optional[str]


class Flight(TypedDict):
    flight_number: Optional[str]
    airline_code: Optional[str]
    airline_name: Optional[str]
    origin_code: Optional[str]
    origin_city: Optional[str]
    destination_code: Optional[str]
    destination_city: Optional[str]
    departure_time: Optional[str]
    arrival_time: Optional[str]
    departure_timestamp: Optional[int]
    arrival_timestamp: Optional[int]
    duration: Optional[str]
    stops: Optional[int]
    layover_cities: List[str]
    legs: List[FlightLeg]
    fare: Optional[float]
    currency: Optional[str]

def build_search_url(
    search_text: str,
    locus_id: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
    children: int = 0,
    rooms: int = 1,
    locus_type: str = "city",
) -> str:
    params = {
        "checkin": checkin,
        "checkout": checkout,
        "roomString": f"{rooms}-{adults}-{children}",
        "searchText": search_text,
        "locusId": locus_id,
        "locusType": locus_type,
    }
    return "https://www.goibibo.com/hotels/hotel-listing/?" + urlencode(params)


def _flight_date(date: str) -> str:
    fmt = "%Y-%m-%d" if "-" in date else "%Y%m%d"
    return datetime.strptime(date, fmt).strftime("%d/%m/%Y")


def build_flight_search_url(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    return_date: Optional[str] = None,
) -> str:
    origin, destination = origin.upper(), destination.upper()
    itinerary = f"{origin}-{destination}-{_flight_date(departure_date)}"
    if return_date:
        itinerary += f"_{destination}-{origin}-{_flight_date(return_date)}"

    params = {
        "itinerary": itinerary,
        "tripType": "R" if return_date else "O",
        "paxType": f"A-{adults}_C-{children}_I-{infants}",
        "intl": "false",
        "cabinClass": "E",
    }
    return f"https://www.goibibo.com/flight/search?{urlencode(params, safe='/')}"


def parse_flight_stream_call(response: ScrapeApiResponse):
    """extract the search-stream-dt API call captured by the browser"""
    calls = [
        call
        for call in response.scrape_result["browser_data"]["xhr_call"]
        if SEARCH_STREAM_DT in call["url"] and (call.get("response") or {}).get("body")
    ]
    if not calls:
        raise RuntimeError("flight search-stream-dt API call not found in captured browser data")

    call = calls[-1]
    body = call["response"]["body"]
    data = {}
    for block in body.split("\n\n"):
        lines = block.split("\n")
        if "event: response" not in lines:
            if "event: error" in lines:
                raw = "".join(line[5:].strip() for line in lines if line.startswith("data:"))
                error = json.loads(gzip.decompress(base64.b64decode(raw))) if raw else {}
                raise RuntimeError(f"search-stream-dt returned an error event: {error.get('error', {}).get('type')}")
            continue
        raw = "".join(line[5:].strip() for line in lines if line.startswith("data:"))
        if raw:
            data = json.loads(gzip.decompress(base64.b64decode(raw)))

    if not data:
        raise RuntimeError("no response event in search-stream-dt SSE body")
    return data


def parse_flights(data: Dict) -> List[Flight]:
    """parse flight cards from a search-stream-dt response"""
    currency = ((data.get("meta") or {}).get("locale") or {}).get("currCode")
    journey_map = data.get("journeyMap") or {}
    flights = []

    for group in data.get("cardList") or []:
        for card in group:
            key = (card.get("journeyKeys") or [None])[0]
            journey = journey_map.get(key) or {}
            legs = ((journey.get("flightDetail") or {}).get("legList")) or []
            first_leg = legs[0] if legs else {}
            last_leg = legs[-1] if legs else {}
            layover = journey.get("layover") or {}

            def _strip(html: Optional[str]) -> Optional[str]:
                return re.sub(r"<[^>]+>", "", html).strip() if html else html

            def _city(leg: Dict, point: str) -> Optional[str]:
                return (leg.get(point) or {}).get("city")

            flights.append(
                Flight(
                    flight_number=card.get("flightNumber"),
                    airline_code=", ".join(card.get("airlineCodes") or []),
                    airline_name=(card.get("simpleAirlineHeading") or {}).get("nm"),
                    origin_code=journey.get("depCityCd"),
                    origin_city=_strip(journey.get("depCity")),
                    destination_code=journey.get("arrCityCd"),
                    destination_city=_strip(journey.get("arrCity")),
                    departure_time=journey.get("depTime"),
                    arrival_time=journey.get("arrTime"),
                    departure_timestamp=journey.get("depTimeStamp"),
                    arrival_timestamp=journey.get("arrTimeStamp"),
                    duration=journey.get("duration") and f"{journey['duration']['h']}h {journey['duration']['m']}m",
                    stops=journey.get("stops"),
                    layover_cities=[c.get("cd") for c in layover.get("layoverCityList") or []],
                    legs=[
                        FlightLeg(
                            flight_number=leg.get("legID"),
                            airline=leg.get("airlinename"),
                            aircraft=_strip((leg.get("aircraft") or {}).get("text")),
                            departure_city=_city(leg, "depart"),
                            departure_time=(leg.get("depart") or {}).get("time"),
                            arrival_city=_city(leg, "arrival"),
                            arrival_time=(leg.get("arrival") or {}).get("time"),
                        )
                        for leg in legs
                    ],
                    fare=card.get("fare"),
                    currency=currency,
                )
            )

    return flights

def parse_listing_call(response: ScrapeApiResponse):
    """extract the listing API call captured by the browser"""
    calls = [
        call
        for call in response.scrape_result["browser_data"]["xhr_call"]
        if LISTING_API in call["url"] and (call.get("response") or {}).get("body")
    ]
    if not calls:
        raise RuntimeError("hotel listing API call not found in captured browser data")

    call = calls[-1]
    data = json.loads(call["response"]["body"])["response"]
    payload = json.loads(call["body"]) if call.get("body") else None
    return call, data, payload


def parse_hotels(data: Dict) -> List[Hotel]:
    """parse hotel cards from a listing API response"""
    currency = data.get("currency")
    hotels = []

    for section in data.get("personalizedSections") or []:
        for item in section.get("hotels") or []:
            price = item.get("priceDetail") or {}
            location = item.get("locationDetail") or {}
            geo = item.get("geoLocation") or {}
            review = item.get("reviewSummaryUgc") or {}
            area = (item.get("locationPersuasion") or [None])[0]
            images = [
                f"https:{url}" if url.startswith("//") else url
                for media in item.get("media") or []
                if (url := media.get("url"))
            ]

            hotels.append(
                Hotel(
                    id=item.get("id"),
                    gi_id=item.get("giId"),
                    name=item.get("name"),
                    property_type=item.get("propertyType"),
                    star_rating=item.get("starRating"),
                    sold_out=item.get("soldOut", False),
                    total_room_count=item.get("totalRoomCount"),
                    categories=item.get("categories") or [],
                    area=area,
                    city=location.get("name"),
                    country=location.get("countryName"),
                    latitude=geo.get("latitude"),
                    longitude=geo.get("longitude"),
                    images=images,
                    price=price.get("discountedPrice", price.get("price")),
                    price_with_tax=price.get("discountedPriceWithTax", price.get("priceWithTax")),
                    price_suffix=price.get("priceSuffix"),
                    currency=currency,
                    rating=review.get("hotelRating"),
                    rating_text=review.get("ratingText"),
                    review_count=review.get("reviewCount"),
                    rating_count=review.get("ratingCount"),
                    amenities=item.get("facilityHighlights") or [],
                    description=item.get("shortDescSeo"),
                    url=item.get("seoUrl") or item.get("detailDeeplinkUrl"),
                )
            )

    return hotels


def _listing_cursor(data: Dict) -> Optional[Dict[str, str]]:
    """read pagination cursor from the listing response"""
    source = data.get("searchCriteria") or data
    window = source.get("lastFetchedWindowInfo")
    if not window:
        return None
    return {
        "lastHotelId": source.get("lastHotelId", ""),
        "lastHotelCategory": source.get("lastHotelCategory", ""),
        "lastFetchedWindowInfo": window,
    }


def _next_listing_request(api_url: str, payload: Dict, cursor: Dict[str, str]):
    """build the next listing page url and POST body"""
    request_id = str(uuid4())
    parsed = urlparse(api_url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    params["ck"] = [str(uuid4())]
    params["requestId"] = [request_id]
    next_url = urlunparse(parsed._replace(query=urlencode(params, doseq=True)))

    next_payload = deepcopy(payload)
    next_payload.setdefault("requestDetails", {})["requestId"] = request_id
    next_payload.setdefault("searchCriteria", {}).update(cursor)
    return next_url, next_payload


async def scrape_hotel_search(
    search_text: str,
    locus_id: str,
    checkin: str,
    checkout: str,
    adults: int = 2,
    children: int = 0,
    rooms: int = 1,
    max_pages: int = 5,
) -> List[Hotel]:
    """Scrape goibibo hotel search; capture the listing API from the search page then paginate until max_pages (copy locus_id from a hotel-listing URL)."""
    url = build_search_url(search_text, locus_id, checkin, checkout, adults, children, rooms)
    session = uuid4().hex
    log.info(f"scraping goibibo hotels for {search_text}: {url}")

    page = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, rendering_wait=10000, wait_for_selector=f"xhr:{LISTING_API}", session=session, **BASE_CONFIG)
    )
    call, data, payload = parse_listing_call(page)
    headers = call["headers"]
    api_url = call["url"]

    hotels = parse_hotels(data)
    seen = {h["id"] for h in hotels}
    log.info(f"page 1: {len(hotels)} hotels")

    cursor = _listing_cursor(data)
    for page_num in range(2, max_pages + 1):
        if not cursor or not payload:
            break

        api_url, body = _next_listing_request(api_url, payload, cursor)
        response = await SCRAPFLY.async_scrape(
            ScrapeConfig(
                api_url,
                method="POST",
                headers=headers,
                body=json.dumps(body),
                session=session,
                render_js=False,
                asp=True,
                country="IN",
            )
        )
        data = json.loads(response.content)["response"]
        page_hotels = parse_hotels(data)
        new_hotels = [h for h in page_hotels if h["id"] not in seen]
        if not new_hotels:
            break

        seen.update(h["id"] for h in new_hotels)
        hotels.extend(new_hotels)
        log.info(f"page {page_num}: +{len(new_hotels)} (total {len(hotels)})")
        cursor = _listing_cursor(data)

    log.success(f"scraped {len(hotels)} hotels for {search_text}")
    return hotels

async def scrape_flight_search(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    return_date: Optional[str] = None,
) -> List[Flight]:
    """Scrape flight search results and return parsed flight data."""
    url = build_flight_search_url(origin, destination, departure_date, adults, children, infants, return_date)
    log.info(f"scraping flight search: {url}")
    js_scenario = [
        {"wait": 5000},
        {
            "condition": {
                "selector": "[data-testid='cta-wrapper'] button",
                "selector_state": "not_existing",
                "action": "exit_success",
            }
        },
        {"click": {"selector": "[data-testid='cta-wrapper'] button"}},
        {"wait": 10000},
    ]
    page = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url,
            rendering_wait=5000,
            js_scenario=js_scenario,
            **BASE_CONFIG,
        )
    )
    data = parse_flight_stream_call(page)
    flights = parse_flights(data)
    log.success(f"scraped {len(flights)} flights for {origin}-{destination}")
    return flights