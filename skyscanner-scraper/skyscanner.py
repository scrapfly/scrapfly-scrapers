"""
This is an example web scraper for skyscanner.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, TypedDict

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "proxy_pool": "public_residential_pool",
    "render_js": True,
    "rendering_wait": 5000,
    "country": "US",
}

SEARCH_XHR_PATH = "/g/radar/api/v2/web-unified-search/"
RESULTS_SORTED_SELECTOR = "//span[contains(text(),'results sorted by')]"

class FlightResult(TypedDict, total=False):
    origin: str
    destination: str
    departure_date: str
    trip_type: str
    market_country: str
    currency: str
    carrier: Optional[str]
    operated_by: Optional[str]
    departure_time: Optional[str]
    arrival_time: Optional[str]
    duration: Optional[str]
    stops: Optional[str]
    price: Optional[str]
    provider_deal_count: Optional[int]
    captured_at: str
    return_date: str
    return_carrier: Optional[str]
    return_operated_by: Optional[str]
    return_departure_time: Optional[str]
    return_arrival_time: Optional[str]
    return_duration: Optional[str]
    return_stops: Optional[str]


class FlightSearch(TypedDict, total=False):
    url: str
    origin: str
    destination: str
    departure_date: str
    return_date: str
    trip_type: str
    market_country: str
    flight_count: int
    flights: List[FlightResult]


def build_url(
    origin: str,
    destination: str,
    yymmdd: str,
    adults: int = 1,
    cabin_class: str = "economy",
    rtn: int = 0,
    return_yymmdd: Optional[str] = None,
) -> str:
    """Build a Skyscanner flight-search URL; round trips need both dates in the path."""
    date_path = f"{yymmdd}/"
    if rtn and return_yymmdd:
        date_path += f"{return_yymmdd}/"
    return (
        f"https://www.skyscanner.com/transport/flights/"
        f"{origin.upper()}/{destination.upper()}/{date_path}"
        f"?adults={adults}&cabinclass={cabin_class}&rtn={rtn}"
    )


def to_yymmdd(departure_date: str) -> str:
    """Convert YYYY-MM-DD to Skyscanner's YYMMDD path segment."""
    return datetime.strptime(departure_date, "%Y-%m-%d").strftime("%y%m%d")


def _format_time(iso_dt: str) -> str:
    dt = datetime.fromisoformat(iso_dt)
    return dt.strftime("%I:%M %p").lstrip("0")


def _format_duration(minutes: int) -> str:
    return f"{minutes // 60}h {minutes % 60:02d}"


def _format_stops(count: int) -> str:
    if count == 0:
        return "Direct"
    if count == 1:
        return "1 stop"
    return f"{count} stops"


def _carrier_name(carriers: List[Dict]) -> Optional[str]:
    return carriers[0]["name"] if carriers else None


def _parse_leg(leg: Dict) -> Dict:
    carrier = _carrier_name(leg["carriers"]["marketing"])
    operator = _carrier_name(leg["carriers"].get("operating", []))
    return {
        "carrier": carrier,
        "operated_by": operator if operator and operator != carrier else None,
        "departure_time": _format_time(leg["departure"]),
        "arrival_time": _format_time(leg["arrival"]),
        "duration": _format_duration(leg["durationInMinutes"]),
        "stops": _format_stops(leg["stopCount"]),
    }


def _parse_flight(
    item: Dict,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str],
    market_country: str,
    captured_at: str,
) -> Optional[FlightResult]:
    legs = item["legs"]
    outbound = _parse_leg(legs[0])
    trip_type = "round_trip" if len(legs) == 2 else "one_way"

    flight = FlightResult(
        origin=origin.upper(),
        destination=destination.upper(),
        departure_date=departure_date,
        trip_type=trip_type,
        market_country=market_country,
        currency="USD",
        carrier=outbound["carrier"],
        operated_by=outbound["operated_by"],
        departure_time=outbound["departure_time"],
        arrival_time=outbound["arrival_time"],
        duration=outbound["duration"],
        stops=outbound["stops"],
        price=item["price"]["formatted"],
        provider_deal_count=len(item["pricingOptions"]),
        captured_at=captured_at,
    )

    if trip_type == "round_trip":
        inbound = _parse_leg(legs[1])
        flight["return_date"] = return_date
        flight["return_carrier"] = inbound["carrier"]
        flight["return_operated_by"] = inbound["operated_by"]
        flight["return_departure_time"] = inbound["departure_time"]
        flight["return_arrival_time"] = inbound["arrival_time"]
        flight["return_duration"] = inbound["duration"]
        flight["return_stops"] = inbound["stops"]

    return flight


def parse_flights_from_xhr(
    xhr_results: List[Dict],
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    market_country: str = "US",
) -> List[FlightResult]:
    """Parse flight itineraries from the web-unified-search XHR JSON response."""
    captured_at = datetime.now(timezone.utc).isoformat()
    flights: List[FlightResult] = []

    for item in xhr_results:
        try:
            flights.append(
                _parse_flight(item, origin, destination, departure_date, return_date, market_country, captured_at)
            )
        except (KeyError, IndexError, ValueError):
            continue

    log.success(f"parsed {len(flights)} flights from {origin}->{destination}")
    return flights


def _extract_xhr_results(xhr_calls: List[Dict]) -> List[Dict]:
    """Extract itinerary results from the latest web-unified-search XHR call."""
    search_calls = [c for c in xhr_calls if SEARCH_XHR_PATH in c["url"]]
    if not search_calls:
        raise RuntimeError(
            "Skyscanner XHR search call not found — try increasing rendering_wait"
        )

    data = json.loads(search_calls[-1]["response"]["body"])
    status = data.get("context", {}).get("status", "unknown")
    log.info(
        f"using XHR response (status={status!r}, {len(search_calls)} calls captured)"
    )

    if "itineraries" not in data:
        raise RuntimeError(
            f"'itineraries' key missing in XHR response (status={status!r})"
        )

    return data["itineraries"]["results"]


async def scrape_flights(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    cabin_class: str = "economy",
    return_date: Optional[str] = None,
    market_country: str = "US",
) -> FlightSearch:
    """Scrape Skyscanner one-way or round-trip flight results via XHR interception."""
    rtn = 1 if return_date else 0
    url = build_url(
        origin,
        destination,
        to_yymmdd(departure_date),
        adults,
        cabin_class,
        rtn=rtn,
        return_yymmdd=to_yymmdd(return_date) if return_date else None,
    )

    trip_desc = f"{departure_date} -> {return_date}" if return_date else departure_date
    log.info(f"scraping skyscanner {origin}->{destination} on {trip_desc}")
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url,
            **BASE_CONFIG,
            wait_for_selector=RESULTS_SORTED_SELECTOR,
        )
    )
    xhr_results = _extract_xhr_results(
        response.scrape_result["browser_data"]["xhr_call"]
    )
    flights = parse_flights_from_xhr(
        xhr_results, origin, destination, departure_date, return_date, market_country
    )

    result = FlightSearch(
        url=url,
        origin=origin.upper(),
        destination=destination.upper(),
        departure_date=departure_date,
        trip_type="round_trip" if rtn else "one_way",
        market_country=market_country,
        flight_count=len(flights),
        flights=flights,
    )
    return result
