"""
This is an example web scraper for google.com/travel/flights.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, TypedDict
from urllib.parse import quote_plus

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "render_js": True,
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


# Click "show more", expand each flight's details, and open the price history panel.
_SHOW_MORE_SCENARIO = [
    {
        "click": {
            "selector": "button[jsname='b3VHJd']",
            "ignore_if_not_visible": True,
            "ignore": True,
        }
    },
    {"wait": 1000},
    {
        "wait_for_selector": {
            "selector": 'button[aria-label="View more flights"]',
            "timeout": 15000,
        }
    },
    {
        "click": {
            "selector": 'button[aria-label="View more flights"]',
            "ignore_if_not_visible": True,
            "ignore": True,
        }
    },
    {"wait": 3000},
    {
        "execute": {
            "script": "document.querySelectorAll('button[aria-label^=\"Flight details\"]').forEach(b => b.click())",
            "timeout": 15000,
        }
    },
    {"wait": 2000}
]


class AirportInfo(TypedDict):
    name: Optional[str]
    id: Optional[str]
    time: Optional[str]


class FlightLeg(TypedDict):
    departure_airport: Optional[AirportInfo]
    arrival_airport: Optional[AirportInfo]
    duration: Optional[str]
    airplane: Optional[str]
    airline: Optional[str]
    airline_logo: Optional[str]
    travel_class: Optional[str]
    flight_number: Optional[str]
    legroom: Optional[str]
    extensions: List[str]


class Layover(TypedDict):
    airport: str
    duration: Optional[str]


class FlightResult(TypedDict):
    airline: Optional[str]
    flight_number: Optional[str]
    departure_time: Optional[str]
    departure_airport: Optional[str]
    arrival_time: Optional[str]
    arrival_airport: Optional[str]
    duration: Optional[str]
    stops: int
    layovers: List[Layover]
    price: Optional[int]
    currency: str
    cabin_class: Optional[str]
    plane_model: Optional[str]
    extensions: List[str]
    legroom: Optional[str]


class FlightSearch(TypedDict):
    search_date: str
    route: str
    departure_date: str
    return_date: Optional[str]
    flights: List[FlightResult]


def build_search_url(
    origin: str,
    destination: str,
    depart: str,
    ret: Optional[str] = None,
    currency: str = "USD",
) -> str:
    """Build a Google Flights search URL. For one way flights, ret is None."""
    if ret:
        query = f"Flights from {origin} to {destination} on {depart} through {ret}"
    else:
        query = f"one way flights from {origin} to {destination} on {depart}"
    return f"https://www.google.com/travel/flights?q={quote_plus(query)}&hl=en&curr={currency}"


def _find(pattern: str, text: str) -> Optional[str]:
    """Return the first regex group from text, or None."""
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def parse_stops(text: Optional[str]) -> int:
    """'Nonstop' -> 0, '1 stop' -> 1, '2 stops' -> 2."""
    if not text or "nonstop" in text.lower():
        return 0
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0


def _arrival_with_suffix(
    dep_full: Optional[str], arr_full: Optional[str]
) -> Optional[str]:
    """Return 'HH:MM' or 'HH:MM+N' when arrival is N days after departure."""
    if dep_full and arr_full:
        try:
            dep_dt = datetime.strptime(dep_full, "%Y-%m-%d %H:%M")
            arr_dt = datetime.strptime(arr_full, "%Y-%m-%d %H:%M")
            diff = (arr_dt.date() - dep_dt.date()).days
            return arr_dt.strftime("%H:%M") + (f"+{diff}" if diff > 0 else "")
        except ValueError:
            pass
    return arr_full


def _parse_layovers(panel) -> List[Layover]:
    """Parse layovers like '3 hr 5 min layover · Vienna (VIE)'."""
    layovers: List[Layover] = []
    for el in panel.css("div.tvtJdb"):
        text = " ".join(el.css("::text").getall())
        code = re.search(r"\(([A-Z]{3})\)", text)
        if code:
            layovers.append(Layover(airport=code.group(1), duration=text))
    return layovers


def _extract_extensions(container) -> List[str]:
    """Pull amenity/condition strings from a card or leg's extension list."""
    items: List[str] = []
    for li in container.css("li.WtSsrd"):
        text = (
            li.css("span.gI4d6d::text").get()
            or li.css("span.g6UICf::text").get()
            or li.xpath("text()[normalize-space()]").get("").strip()
        )
        if text:
            items.append(text)
    return items


def parse_flight_legs(panel, year: int) -> List[FlightLeg]:
    """Parse each leg inside an expanded flight detail panel."""
    legs: List[FlightLeg] = []
    for leg in panel.css("div[jsname='lVbzR']"):
        logo_style = leg.css("[style*='airline_logos/70px/']::attr(style)").get() or ""
        logo = re.search(r"url\((https://[^)]+\.png)\)", logo_style)

        # Airline name and aircraft model — skip the flight-number, class, and duplicate spans.
        plain = [
            s.css("::text").get()
            for s in leg.css("div.MX5RWe span.Xsgmwe")
            if "sI2Nye" not in s.attrib.get("class", "")
            and s.attrib.get("jsname", "") != "Pvlywd"
            and "QS0io" not in s.attrib.get("class", "")
        ]
        airline = plain[0] if plain else None
        airplane = plain[-1] if len(plain) > 1 else (plain[0] if plain else None)

        fn_raw = leg.css("div.MX5RWe span.Xsgmwe.sI2Nye::text").get()
        flight_number = fn_raw.replace("\xa0", " ") if fn_raw else None

        dep_name = (leg.css("div.ZHa2lc::text").get() or "").strip()
        dep_code = (leg.css("div.ZHa2lc span[dir='ltr']::text").get() or "").strip("()")
        arr_name = (leg.css("div.FY5t7d::text").get() or "").strip()
        arr_code = (leg.css("div.FY5t7d span[dir='ltr']::text").get() or "").strip("()")

        extensions = _extract_extensions(leg)
        legroom = next(
            (
                m.group(1)
                for ext in extensions
                if (m := re.search(r"legroom\s*\((\d+ in)\)", ext, re.IGNORECASE))
            ),
            None,
        )

        legs.append(
            FlightLeg(
                departure_airport=AirportInfo(
                    name=dep_name or None, id=dep_code or None, time=leg.css("div.ZHa2lc::text").get()
                ),
                arrival_airport=AirportInfo(
                    name=arr_name or None, id=arr_code or None, time=leg.css("div.FY5t7d::text").get()
                ),
                duration=leg.css("div.P102Lb::text").get(),
                airplane=airplane,
                airline=airline,
                airline_logo=logo.group(1) if logo else None,
                travel_class=leg.css("span[jsname='Pvlywd']::text").get(),
                flight_number=flight_number,
                legroom=legroom,
                extensions=extensions,
            )
        )
    return legs


def _flight_number_from_card(card) -> Optional[str]:
    """Pull '<airline> <number>' from the TravelImpactModel data attribute."""
    url = (
        card.css(
            "[data-travelimpactmodelwebsiteurl]::attr(data-travelimpactmodelwebsiteurl)"
        ).get()
        or ""
    )
    m = re.search(r"[A-Z]+-[A-Z]+-([A-Z]\w+)-(\d+)-\d{8}", url)
    return f"{m.group(1)} {m.group(2)}" if m else None


def _card_extensions(card, panel) -> List[str]:
    """Deduplicated extension/amenity strings across all legs and card-level conditions."""
    seen, out = set(), []
    for text in _extract_extensions(panel) + [
        t.strip() for t in card.css("div.U0scI div::text").getall() if t.strip()
    ]:
        if text not in seen:
            seen.add(text)
            out.append(text)
    return out



def parse_flights(
    response: ScrapeApiResponse, year: int = 0, currency: str = "USD"
) -> List[FlightResult]:
    """Parse a Google Flights search page into a list of FlightResult records."""
    flights: List[FlightResult] = []
    seen_labels: set = set()

    for card in response.selector.css("li.pIav2d"):
        label = card.css("div[role='link']::attr(aria-label)").get() or ""
        if not label or label in seen_labels:
            continue
        seen_labels.add(label)

        panel = card.css("div[jsname='XxAJue']")
        legs = parse_flight_legs(panel, year)
        first_leg, last_leg = (legs[0] if legs else None), (legs[-1] if legs else None)

        dep_full = (
            (first_leg["departure_airport"] or {}).get("time") if first_leg else None
        )
        arr_full = (last_leg["arrival_airport"] or {}).get("time") if last_leg else None
        dep_time = dep_full or card.css(
            "span[aria-label^='Departure time']::text"
        ).get()
        arr_time = _arrival_with_suffix(dep_full, arr_full) or card.css(
            "span[aria-label^='Arrival time']::text"
        ).get()

        price = _find(r"From (\d[\d,]*) \w+ dollars", label) or 0
        duration_label = (
            card.css("div[aria-label^='Total duration']::attr(aria-label)").get() or ""
        )

        flights.append(
            FlightResult(
                airline=_find(r"flight with (.+?)\.", label),
                flight_number=_flight_number_from_card(card),
                departure_time=dep_time,
                departure_airport=(first_leg["departure_airport"] or {}).get("id") if first_leg else None,
                arrival_time=arr_time,
                arrival_airport=(last_leg["arrival_airport"] or {}).get("id") if last_leg else None,
                duration=duration_label,
                stops=parse_stops(_find(r"(Nonstop|\d+ stops?)", label)),
                layovers=_parse_layovers(panel),
                price=price,
                currency=currency,
                cabin_class=(first_leg.get("travel_class") or "").lower() if first_leg else None,
                plane_model=first_leg.get("airplane") if first_leg else None,
                extensions=_card_extensions(card, panel),
                legroom=first_leg.get("legroom") if first_leg else None,
            )
        )

    log.success(f"parsed {len(flights)} flights")
    return flights


async def scrape_flights(
    origin: str,
    destination: str,
    depart: str,
    ret: Optional[str] = None,
    currency: str = "USD",
) -> FlightSearch:
    """Scrape Google Flights results for a route and date(s)."""
    url = build_search_url(origin, destination, depart, ret, currency)
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, **BASE_CONFIG, js_scenario=_SHOW_MORE_SCENARIO)
    )
    year = int(depart.split("-")[0]) if depart else 0
    return FlightSearch(
        search_date=datetime.now().strftime("%Y-%m-%d"),
        route=f"{origin}-{destination}",
        departure_date=depart,
        return_date=ret,
        flights=parse_flights(response, year=year, currency=currency),
    )


def store_results(route: str, depart: str, ret: str | None, flights: List[FlightResult]) -> None:
    history_file = output / "flights_history.json"
    records = json.loads(history_file.read_text()) if history_file.exists() else []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for f in flights:
        records.append({
            "scraped_at": now,
            "route": route,
            "depart_date": depart,
            "return_date": ret,
            "airline": f["airline"],
            "price": f["price"],
            "stops": f["stops"],
        })
    history_file.write_text(json.dumps(records, indent=2))


def historical_min(route: str, depart: str) -> Optional[int]:
    history_file = output / "flights_history.json"
    if not history_file.exists():
        return None
    records = json.loads(history_file.read_text())
    prices = [int(r["price"]) for r in records if r["route"] == route and r["depart_date"] == depart and r["price"]]
    return min(prices) if prices else None


async def track_route(origin: str, destination: str, depart: str, ret: str) -> None:
    route = f"{origin}-{destination}"
    flights = (await scrape_flights(origin, destination, depart, ret))["flights"]
    prices = [f["price"] for f in flights if f["price"]]
    if not prices:
        return
    new_min = min(int(p) for p in prices)
    old_min = historical_min(route, depart)
    store_results(route, depart, ret, flights)
    if old_min is not None and new_min < old_min:
        log.success(f"price drop on {route} {depart}: {old_min} -> {new_min}")


