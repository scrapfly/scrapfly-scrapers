"""
This is an example web scraper for google.com/travel/flights.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import re
from datetime import datetime
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
    {"wait": 1000},
    {
        "click": {
            "selector": 'button[aria-label="View price history"]',
            "ignore_if_not_visible": True,
            "ignore": True,
        }
    },
    {"wait": 1000},
]


class AirportInfo(TypedDict):
    name: Optional[str]
    id: Optional[str]
    time: Optional[str]


class FlightLeg(TypedDict):
    departure_airport: Optional[AirportInfo]
    arrival_airport: Optional[AirportInfo]
    duration: Optional[int]
    airplane: Optional[str]
    airline: Optional[str]
    airline_logo: Optional[str]
    travel_class: Optional[str]
    flight_number: Optional[str]
    legroom: Optional[str]
    extensions: List[str]


class Layover(TypedDict):
    airport: str
    duration_minutes: int


class FlightResult(TypedDict):
    airline: Optional[str]
    flight_number: Optional[str]
    departure_time: Optional[str]
    departure_airport: Optional[str]
    arrival_time: Optional[str]
    arrival_airport: Optional[str]
    duration_minutes: Optional[int]
    stops: int
    layovers: List[Layover]
    price: Optional[int]
    currency: str
    price_level: Optional[str]
    cabin_class: Optional[str]
    plane_model: Optional[str]
    co2_kg: Optional[int]
    co2_vs_typical: Optional[str]
    extensions: List[str]
    legroom: Optional[str]
    booking_token: Optional[str]
    type: Optional[str]


class FlightSearch(TypedDict):
    search_date: str
    route: str
    departure_date: str
    return_date: Optional[str]
    flights: List[FlightResult]


class BookingOption(TypedDict):
    book_with: str
    airline: bool
    airline_logos: List[str]
    option_title: str
    price: Optional[int]
    price_usd: Optional[int]
    extensions: List[str]
    baggage_prices: List[str]

class BookingResult(TypedDict):
    booking_options: List[BookingOption]


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


def parse_price(text: str) -> Optional[int]:
    """'$1,234' -> 1234"""
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else None


def parse_co2(text: Optional[str]) -> Optional[int]:
    """'612 kg CO2e' -> 612"""
    match = re.search(r"(\d[\d,]*)\s+kg CO2e", text or "")
    return int(match.group(1).replace(",", "")) if match else None


def parse_duration_minutes(text: Optional[str]) -> Optional[int]:
    """'8 hr 40 min' -> 520"""
    hrs = re.search(r"(\d+)\s*hr", text or "")
    mins = re.search(r"(\d+)\s*min", text or "")
    if not (hrs or mins):
        return None
    return (int(hrs.group(1)) if hrs else 0) * 60 + (int(mins.group(1)) if mins else 0)


def _to_24h(time_str: Optional[str]) -> Optional[str]:
    """'7:21 PM' or '2026-09-15 19:21' -> '19:21'."""
    if not time_str:
        return None
    if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", time_str):
        return time_str.split(" ")[1]
    for fmt in ("%I:%M %p", "%I:%M%p"):
        try:
            return datetime.strptime(time_str.strip(), fmt).strftime("%H:%M")
        except ValueError:
            continue
    return None


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
    return _to_24h(arr_full)


def _price_level(
    price: Optional[int], low: Optional[int], high: Optional[int]
) -> Optional[str]:
    """Classify price as 'low', 'typical', or 'high' using Google's typical price range."""
    if price is None or low is None or high is None:
        return None
    if price <= low:
        return "low"
    if price >= high:
        return "high"
    return "typical"


def _parse_layovers(panel) -> List[Layover]:
    """Parse layovers like '3 hr 5 min layover · Vienna (VIE)'."""
    layovers: List[Layover] = []
    for el in panel.css("div.tvtJdb"):
        text = " ".join(el.css("::text").getall())
        code = re.search(r"\(([A-Z]{3})\)", text)
        dur = parse_duration_minutes(text)
        if code and dur is not None:
            layovers.append(Layover(airport=code.group(1), duration_minutes=dur))
    return layovers


def _parse_leg_datetime(raw: Optional[str], year: int) -> Optional[str]:
    """'9:45 PM on Thu, May 14' + year -> '2026-05-14 21:45'."""
    if not raw or not year:
        return None
    m = re.search(
        r"(\d+:\d+\s+[AP]M)\s+on\s+\w+,\s+(\w+)\s+(\d+)",
        raw.replace("\xa0", " "),
        re.IGNORECASE,
    )
    if not m:
        return None
    try:
        dt = datetime.strptime(
            f"{m.group(2)} {int(m.group(3)):02d} {year} {m.group(1)}",
            "%b %d %Y %I:%M %p",
        )
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return None


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

        dep_dates = leg.css(
            "div.dPzsIb div[jsname='bN97Pc'] span.eoY5cb::text"
        ).getall()
        arr_dates = leg.css(
            "div.SWFQlc div[jsname='bN97Pc'] span.eoY5cb::text"
        ).getall()
        dep_time = _parse_leg_datetime(dep_dates[0] if dep_dates else None, year)
        arr_time = _parse_leg_datetime(arr_dates[0] if arr_dates else None, year)

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
                    name=dep_name or None, id=dep_code or None, time=dep_time
                ),
                arrival_airport=AirportInfo(
                    name=arr_name or None, id=arr_code or None, time=arr_time
                ),
                duration=parse_duration_minutes(leg.css("div.P102Lb::text").get()),
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


def _typical_price_range(
    response: ScrapeApiResponse,
) -> tuple[Optional[int], Optional[int]]:
    """Read the (low, high) range from Google's 'Price Insights' section."""
    text = response.selector.css("div.NtS4zd::text").get() or ""
    m = re.search(r"([\d,]+)[–\-]([\d,]+)", text)
    if not m:
        return None, None
    return parse_price(m.group(1)), parse_price(m.group(2))


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


def _co2_from_card(card) -> tuple[Optional[int], Optional[str]]:
    """Return (co2_kg, vs_typical) parsed from data attributes."""
    el = card.css("[data-co2currentflight]")
    if not el:
        return None, None
    kg = int(el.attrib.get("data-co2currentflight", 0)) // 1000
    diff = int(el.attrib.get("data-percentagediff", 0))
    vs = "avg" if diff == 0 else f"{'+' if diff > 0 else ''}{diff}%"
    return kg, vs


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



def _build_booking_scenario(booking_token: str) -> list:
    """Build a js_scenario that selects the outbound flight then the first return flight."""
    escaped = booking_token.replace('"', '\\"')
    # Full comma-separated itinerary (e.g. "JFK-ZRH-LX-17-20260516,ZRH-CDG-LX-1234-20260517")
    # is unique per card — a single substring match is sufficient
    click_outbound_js = (
        f"var el=document.querySelector('[data-travelimpactmodelwebsiteurl*=\"{escaped}\"]');"
        "var outCard=el&&el.closest('li.pIav2d');"
        "if(outCard){var btn=outCard.querySelector('.VfPpkd-RLmnJb');if(btn)btn.click();}"
    )
    # After outbound click Google shows return flights — click the first card that is NOT the outbound one
    click_return_js = (
        f"var el=document.querySelector('[data-travelimpactmodelwebsiteurl*=\"{escaped}\"]');"
        "var outCard=el&&el.closest('li.pIav2d');"
        "var cards=document.querySelectorAll('li.pIav2d');"
        "for(var i=0;i<cards.length;i++){"
        "if(cards[i]!==outCard){var btn=cards[i].querySelector('.VfPpkd-RLmnJb');if(btn){btn.click();break;}}}"
    )
    return [
        {"click": {"selector": "button[jsname='b3VHJd']", "ignore_if_not_visible": True, "ignore": True}},
        {"wait": 1000},
        {"wait_for_selector": {"selector": 'button[aria-label="View more flights"]', "timeout": 15000}},
         {"wait": 3000},
        {"click": {"selector": 'button[aria-label="View more flights"]', "ignore_if_not_visible": True, "ignore": True}},
        {"wait": 3000},
        {
        "execute": {
            "script": "document.querySelectorAll('button[aria-label^=\"Flight details\"]').forEach(btn => btn.click())",
            "timeout": 15000,
        }
        },
        {"execute": {"script": click_outbound_js, "timeout": 5000}},
        {"wait": 1000},
        {"execute": {"script": click_return_js, "timeout": 5000}},
        {"wait": 5000},
        {"wait_for_selector": {"selector": 'div[jsname="DDLpqe"]', "timeout": 15000}},        
    ]

def parse_flights(
    response: ScrapeApiResponse, year: int = 0, currency: str = "USD"
) -> List[FlightResult]:
    """Parse a Google Flights search page into a list of FlightResult records."""
    price_low, price_high = _typical_price_range(response)
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

        # Extract the booking token from the tim_url
        tim_url = card.css("[data-travelimpactmodelwebsiteurl]::attr(data-travelimpactmodelwebsiteurl)").get() or ""
        itin_match = re.search(r"itinerary=([A-Z]+-[A-Z]+-[A-Z]+-\d+-\d+(?:,[A-Z]+-[A-Z]+-[A-Z]+-\d+-\d+)*)", tim_url)
        booking_token = itin_match.group(1) if itin_match else None

        dep_full = (
            (first_leg["departure_airport"] or {}).get("time") if first_leg else None
        )
        arr_full = (last_leg["arrival_airport"] or {}).get("time") if last_leg else None
        dep_time = _to_24h(dep_full) or _to_24h(
            card.css("span[aria-label^='Departure time']::text").get()
        )
        arr_time = _arrival_with_suffix(dep_full, arr_full) or _to_24h(
            card.css("span[aria-label^='Arrival time']::text").get()
        )

        co2_kg, co2_vs = _co2_from_card(card)
        price = parse_price(_find(r"From (\d[\d,]*) \w+ dollars", label) or "")
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
                duration_minutes=parse_duration_minutes(duration_label),
                stops=parse_stops(_find(r"(Nonstop|\d+ stops?)", label)),
                layovers=_parse_layovers(panel),
                price=price,
                currency=currency,
                price_level=_price_level(price, price_low, price_high),
                cabin_class=(first_leg.get("travel_class") or "").lower() if first_leg else None,
                plane_model=first_leg.get("airplane") if first_leg else None,
                co2_kg=co2_kg,
                co2_vs_typical=co2_vs,
                extensions=_card_extensions(card, panel),
                legroom=first_leg.get("legroom") if first_leg else None,
                booking_token=booking_token,
                type="Round trip" if "round trip" in label.lower() else "One way",
            )
        )

    log.success(f"parsed {len(flights)} flights")
    return flights


def parse_booking(response: ScrapeApiResponse) -> BookingResult:
    """Parse the Google Flights booking options page into selected flights and booking options."""
    sel = response.selector

    options: List[BookingOption] = []
    for group in sel.css("div[jsname='DDLpqe'] div.rRu7ob"):
        header = group.css("div.L53Hhb")
        logo_style = header.css("div.MnHIn[style*='airline_logos']::attr(style)").get() or ""
        logo_m = re.search(r"url\((https://[^)]+\.png)\)", logo_style)
        name_raw = header.css("div.ogfYpf.AdWm1c::text").get() or ""
        book_with = re.sub(r"^Book with\s*", "", name_raw, flags=re.IGNORECASE).strip()
        is_airline = "airline" in (header.css("div.sSHqwe.wZlgrf::text").get() or "").lower()

        for card in group.css("div.G2p4Wb div.Cbm5nb"):
            usd_label = card.css("div.T5Qxqc span[data-gs]::attr(aria-label)").get() or ""
            baggage = []
            for bag_li in card.css("ul.BABTTc li.oi0btb"):
                text = (
                    bag_li.attrib.get("aria-label", "").strip()
                    or "".join(bag_li.css("span[aria-hidden='true']::text").getall()).strip()
                    or "".join(bag_li.css("::text").getall()).strip()
                )
                if text:
                    baggage.append(text)
            options.append(BookingOption(
                book_with=book_with,
                airline=is_airline,
                airline_logos=[logo_m.group(1)] if logo_m else [],
                option_title=card.css("h3.DllrY.ogfYpf::text").get() or "",
                price=parse_price((card.css("span.tZe0ff::text").get() or "").replace("\xa0", "")),
                price_usd=parse_price(_find(r"(\d[\d,]*)\s+US dollars", usd_label) or ""),
                extensions=[t for t in card.css("ul.jTLypf li.OFerGc span.hEkLUb::text").getall() if t.strip()],
                baggage_prices=baggage,
            ))

    log.success(f"parsed booking: {len(options)} booking options")
    return BookingResult(booking_options=options)


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
    

async def scrape_booking(
    origin: str,
    destination: str,
    depart: str,
    ret: Optional[str] = None,
    currency: str = "USD",
    booking_token: str = "",
) -> BookingResult:
    """Navigate to the flight search, select the outbound and return flights, and parse booking options."""
    url = build_search_url(origin, destination, depart, ret, currency)
    scenario = _build_booking_scenario(booking_token)
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, **BASE_CONFIG, timeout=150000, retry=False, js_scenario=scenario)
    )
    return parse_booking(response)
