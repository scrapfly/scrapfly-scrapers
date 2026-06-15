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
    "country": "US",
}

SEARCH_XHR_PATH = "/g/radar/api/v2/web-unified-search/"
RESULTS_SORTED_SELECTOR = "//span[contains(text(),'results sorted by')]"

class FlightResult(TypedDict):
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


class FlightSearch(TypedDict):
    url: str
    origin: str
    destination: str
    departure_date: str
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
) -> str:
    """Build a Skyscanner flight-search URL from IATA codes and a YYMMDD date string."""
    return (
        f"https://www.skyscanner.com/transport/flights/"
        f"{origin.upper()}/{destination.upper()}/{yymmdd}/"
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


def _parse_flight(
    item: Dict,
    origin: str,
    destination: str,
    departure_date: str,
    market_country: str,
    captured_at: str,
) -> Optional[FlightResult]:
    legs = item["legs"]
    leg = legs[0]
    trip_type = "round_trip" if len(legs) == 2 else "one_way"

    carrier = _carrier_name(leg["carriers"]["marketing"])
    operator = _carrier_name(leg["carriers"]["operating"])
    operated_by = operator if operator and operator != carrier else None

    return FlightResult(
        origin=origin.upper(),
        destination=destination.upper(),
        departure_date=departure_date,
        trip_type=trip_type,
        market_country=market_country,
        currency="USD",
        carrier=carrier,
        operated_by=operated_by,
        departure_time=_format_time(leg["departure"]),
        arrival_time=_format_time(leg["arrival"]),
        duration=_format_duration(leg["durationInMinutes"]),
        stops=_format_stops(leg["stopCount"]),
        price=item["price"]["formatted"],
        provider_deal_count=len(item["pricingOptions"]),
        captured_at=captured_at,
    )


def parse_flights_from_xhr(
    xhr_results: List[Dict],
    origin: str,
    destination: str,
    departure_date: str,
    market_country: str = "US",
) -> List[FlightResult]:
    """Parse flight itineraries from the web-unified-search XHR JSON response."""
    captured_at = datetime.now(timezone.utc).isoformat()
    flights: List[FlightResult] = []

    for item in xhr_results:
        try:
            flights.append(
                _parse_flight(item, origin, destination, departure_date, market_country, captured_at)
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
    rtn: int = 0,
    market_country: str = "US",
) -> FlightSearch:
    """Scrape Skyscanner one-way or round-trip flight results via XHR interception."""
    url = build_url(
        origin, destination, to_yymmdd(departure_date), adults, cabin_class, rtn
    )

    log.info(f"scraping skyscanner {origin}->{destination} on {departure_date}")
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url,
            **BASE_CONFIG,
            rendering_wait=5000,
            wait_for_selector=RESULTS_SORTED_SELECTOR,
        )
    )
    xhr_results = _extract_xhr_results(
        response.scrape_result["browser_data"]["xhr_call"]
    )
    flights = parse_flights_from_xhr(
        xhr_results, origin, destination, departure_date, market_country
    )

    return FlightSearch(
        url=url,
        origin=origin.upper(),
        destination=destination.upper(),
        departure_date=departure_date,
        trip_type="round_trip" if rtn else "one_way",
        market_country=market_country,
        flight_count=len(flights),
        flights=flights,
    )
