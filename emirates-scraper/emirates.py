"""
This is an example web scraper for emirates.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, TypedDict

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "proxy_pool": "public_residential_pool",
    "render_js": True,
}

BRANDED_FARES_URL = "https://www.emirates.com/service/search-results/branded-fares"

CARRIER_NAMES = {"EK": "Emirates"}
CABIN_NAMES = {"Y": "economy", "W": "premium economy", "J": "business", "F": "first"}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


class FarePrice(TypedDict):
    amount: int
    currency: str


class FlightResult(TypedDict):
    airline: str
    flight_number: str
    departure_time: str
    departure_airport: str
    arrival_time: str
    arrival_airport: str
    duration: str
    stops: int
    layovers: List[dict]
    price: FarePrice
    cabin_class: str
    plane_model: str
    fare_brand: str
    seats_available: int
    captured_at: str


class FlightSearch(TypedDict):
    locale: str
    trip_type: str
    origin: str
    destination: str
    route: str
    search_date: str
    departure_date: str
    return_date: Optional[str]
    lowest_fare: FarePrice
    flights: List[FlightResult]


def _date_click_script(date_iso: str) -> str:
    parsed_date = datetime.strptime(date_iso, "%Y-%m-%d")
    date_label = f"{parsed_date.strftime('%A')}, {parsed_date.day}  {parsed_date.strftime('%B %Y')}"
    date_alt = f"{parsed_date.strftime('%A')}, {parsed_date.strftime('%B')} {parsed_date.day}, {parsed_date.year}"
    return (
        f"document.querySelector('[aria-label*=\"{date_label}\"]')"
        f"?.click() || document.querySelector('[aria-label*=\"{date_alt}\"]')?.click();"
    )


def _pick_airport_option(code: str) -> str:
    return (
        "var items=[...document.querySelectorAll('[data-testid^=\"options_\"]')];"
        f"(items.find(o=>o.textContent.includes('{code}'))||items[0])?.click();"
    )


def _fill_airport(field: str, code: str) -> list:
    return [
        {"fill": {"selector": f"[data-testid^='combobox_{field}'] input", "value": code, "clear": True}},
        {"wait": 1000},
        {"wait_for_selector": {"selector": "[data-testid^='options_']", "timeout": 10000}},
        {"execute": {"script": _pick_airport_option(code)}},
    ]


def _select_date(date_iso: str, picker: str) -> list:
    return [
        {"click": {"selector": picker, "timeout": 5000}},
        {"wait": 1000},
        {"execute": {"script": _date_click_script(date_iso)}},
    ]


def _build_search_scenario(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
) -> list:
    scenario = [
        {"click": {"selector": "button[id*='onetrust-accept']", "ignore": True, "ignore_if_not_visible": True, "timeout": 10000}},
        {"wait": 1000},
    ]

    if not return_date:
        scenario.append(
            {
                "execute": {
                    "script": "[...document.querySelectorAll('button[role=tab]')].find(b=>b.textContent.trim()==='One way')?.click();"
                }
            }
        )

    scenario += _fill_airport("Departure", origin)
    scenario += _fill_airport("Arrival", destination)

    if return_date:
        scenario += _select_date(departure_date, "#startDate")
        scenario += _select_date(return_date, "#endDate")
    else:
        scenario += _select_date(departure_date, "#date-input0, #startDate")

    scenario += [
        {"click": {"selector": "button.rsw-submit-button", "timeout": 10000}},
        {"wait": 3000},
        {"click": {"selector": ".bottom-block__continue button", "ignore": True, "ignore_if_not_visible": True, "timeout": 10000}},
        {"wait": 2000},
    ]
    return scenario


def _format_arrival_time(departure_iso: str, arrival_iso: str) -> str:
    departure = datetime.fromisoformat(departure_iso)
    arrival = datetime.fromisoformat(arrival_iso)
    day_diff = (arrival.date() - departure.date()).days
    return arrival.strftime("%H:%M") + (f"+{day_diff}" if day_diff > 0 else "")


def _parse_layovers(segments: list) -> List[dict]:
    layovers = []
    for segment in segments:
        for stop in segment.get("stopDetails") or []:
            layovers.append({"airport": stop["arrival"], "duration": stop["duration"]})
        if segment.get("connection"):
            layovers.append(
                {"airport": segment["departure"], "duration": segment.get("connectionLayover")}
            )
    return layovers


def parse_branded_fares(response: ScrapeApiResponse) -> dict:
    """Parse branded-fares API response from captured XHR calls."""
    _xhr_calls = response.scrape_result["browser_data"]["xhr_call"]
    for xhr in _xhr_calls:
        if "search-results/branded-fares" not in xhr.get("url", "") or not xhr.get("response"):
            continue
        return json.loads(xhr["response"]["body"])
    raise ValueError("branded-fares xhr call not found")


def parse_lowest_fare(data: dict) -> FarePrice:
    """Parse search-wide lowest fare from branded-fares API response."""
    currency = data.get("currency", {}).get("sale", {}).get("code", "")
    amount = data["lowestFare"]["total"][0]["amount"]
    return FarePrice(amount=amount, currency=currency)


def parse_flight_offers(data: dict) -> List[FlightResult]:
    """Parse branded-fares API response into flight results"""
    currency = data.get("currency", {}).get("sale", {}).get("code", "")
    flights: List[FlightResult] = []

    for bound in data.get("bounds", []):
        for option in bound.get("options", []):
            segments = option.get("airSegments", [])
            if not segments:
                continue

            first_segment = segments[0]
            last_segment = segments[-1]
            layovers = _parse_layovers(segments)
            departure_time = datetime.fromisoformat(first_segment["departureDateTime"]).strftime("%H:%M")
            arrival_time = _format_arrival_time(
                first_segment["departureDateTime"], last_segment["arrivalDateTime"]
            )
            flight_number = " / ".join(
                f"{segment['carrierCode']} {segment['flightNumber']}"
                for segment in segments
                if segment.get("segmentType") == "FLT"
            )

            for cabin in option.get("cabins", []):
                for brand in cabin.get("brandInformation") or []:
                    if brand.get("status") != "AVAILABLE":
                        continue

                    fare_amount = brand["priceDetails"]["summary"]["total"][0]["amount"]
                    carrier_code = first_segment.get("carrierCode", "")
                    cabin_code = brand.get("cabinClass") or cabin.get("cabinClass", "")
                    flights.append(
                        FlightResult(
                            airline=CARRIER_NAMES.get(carrier_code, carrier_code),
                            flight_number=flight_number,
                            departure_time=departure_time,
                            departure_airport=first_segment["departure"],
                            arrival_time=arrival_time,
                            arrival_airport=last_segment["arrival"],
                            duration=option.get("ondDuration", ""),
                            stops=option.get("numberOfConnections", 0),
                            layovers=layovers,
                            price=FarePrice(
                                amount=fare_amount,
                                currency=currency,
                            ),
                            cabin_class=CABIN_NAMES.get(cabin_code, cabin_code),
                            plane_model=first_segment.get("aircraftType", ""),
                            fare_brand=brand.get("fareBrand", ""),
                            seats_available=brand.get("seatsAvailable", 0),
                            captured_at=datetime.now().isoformat(),
                        )
                    )

    log.success(f"parsed {len(flights)} flight offers")
    return flights

async def scrape_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    locale: str = "us/english",
) -> FlightSearch:
    """Scrape flights from emirates.com"""
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            f"https://www.emirates.com/{locale}/book/",
            **BASE_CONFIG,
            js_scenario=_build_search_scenario(origin, destination, departure_date, return_date),
        )
    )
    data = parse_branded_fares(response)
    return FlightSearch(
        locale=locale,
        trip_type="return" if return_date else "one-way",
        origin=origin,
        destination=destination,
        route=f"{origin}-{destination}",
        search_date=datetime.now().strftime("%Y-%m-%d"),
        departure_date=departure_date,
        return_date=return_date,
        lowest_fare=parse_lowest_fare(data),
        flights=parse_flight_offers(data),
    )
