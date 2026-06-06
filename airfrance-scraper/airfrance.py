"""
This is an example cloud browser scraper for Air France.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
from scrapfly import ScrapflyClient, BrowserConfig
from playwright.sync_api import sync_playwright
import uuid
from datetime import datetime
from typing import List, Optional, TypedDict


BROWSER_CONFIG = BrowserConfig(
        debug=True,
        country="FR",
        proxy_pool="residential",
        session=uuid.uuid4().hex,
    )


client = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])


class Layover(TypedDict):
    airport: str
    duration_minutes: Optional[int]


class Flight(TypedDict):
    airline: str
    flight_number: str
    departure_time: str
    departure_airport: str
    arrival_time: str
    arrival_airport: str
    arrives_next_days: int
    duration_minutes: int
    stops: int
    layovers: List[Layover]
    price: str
    currency: str
    cabin_class: str
    seats_available: Optional[int]
    is_promo: bool
    promo_title: Optional[str]
    has_special_fare: bool
    seat_map_eligible: bool
    plane_model: str
    co2_kg: int
    airport_change_warning: Optional[List[str]]

GQL_BOOKING_OP = "operationName=SearchResultAvailableOffersQuery"
SEARCH_BUTTON = "[data-testid='bwsfe-widget__search-button']"
SEARCH_BUTTON_LOADING = f"{SEARCH_BUTTON} .bwc-button-content--loading"
LANDING_URL = "https://wwws.airfrance.fr/"

def _start_xhr_collector(page) -> tuple[list[dict], object]:
    """Collect all XHR/fetch JSON responses into a list. Returns (list, handler)."""
    collected: list[dict] = []

    def on_response(response) -> None:
        if response.request.resource_type not in ("xhr", "fetch") or response.status != 200:
            return
        try:
            payload = response.json()
            collected.append({"url": response.url, "payload": payload})
        except Exception:
            pass

    page.on("response", on_response)
    return collected, on_response


def _date_to_day_id(date_str: str) -> str:
    """Convert YYYY-MM-DD to the bwc-day ID format used by Air France (0-indexed month, no leading zeros)."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{d.year}_{d.month - 1}_{d.day}"


def open_session():
    p = sync_playwright().start()
    cdp_url = client.cloud_browser(BROWSER_CONFIG)
    browser = p.chromium.connect_over_cdp(cdp_url, timeout=180_000)
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else context.new_page()
    page.set_viewport_size({"width": 1280, "height": 800})
    return p, browser, page


def dismiss_cookie_banner(page):
    try:
        page.wait_for_selector("#accept_cookies_btn", timeout=15000)
        page.evaluate("() => document.querySelector('#accept_cookies_btn')?.click()")
        page.wait_for_selector("[data-testid='bwsfe-widget__trip-type-selector']", timeout=15000)
        page.wait_for_selector("[data-testid='bwsfe-widget__search-button']", timeout=15000)
    except Exception:
        pass


def fill_station(page, origin: str, destination: str) -> None:
    for role, iata_code in (("origin", origin), ("destination", destination)):
        picker = page.locator(
            f"[data-testid='bwsfe-connection-picker__station-picker--{role}']"
        )
        field = picker.locator("[data-testid='bwsfe-station-picker__input']").first
        field.scroll_into_view_if_needed()
        field.click(force=True)
        page.wait_for_timeout(800)
        page.keyboard.type(iata_code, delay=80)
        page.wait_for_timeout(1800)
        page.keyboard.press("Enter")
        page.wait_for_timeout(800)


def pick_date(page, date: str, return_date: str) -> None:
    page.wait_for_selector('[data-testid="bwsfe-datepicker__toggle-button"]', timeout=15000)
    day_sel = f"#bwc-day_{_date_to_day_id(date)}"

    page.evaluate(
        "var btn=document.querySelector('[data-testid=\"bwsfe-datepicker__toggle-button\"]');"
        "if(btn&&btn.getAttribute('aria-expanded')!=='true')btn.click();"
    )
    page.wait_for_timeout(1500)

    page.click(day_sel)
    page.wait_for_timeout(500)

    page.click(f"#bwc-day_{_date_to_day_id(return_date)}")
    page.wait_for_timeout(500)

    page.evaluate(
        "() => document.querySelector('[data-testid=\"bwc-calendar__confirm\"]')?.click()"
    )


def _is_search_button_loading(page) -> bool:
    return page.locator(SEARCH_BUTTON_LOADING).count() > 0



def _fill_search_form(
    page,
    origin: str,
    destination: str,
    date: str,
    return_date: str,
) -> None:
    for attempt in range(2):
        if attempt > 0:
            page.reload(wait_until="domcontentloaded", timeout=30000)
        dismiss_cookie_banner(page)
        pick_date(page, date, return_date)
        fill_station(page, origin, destination)
        page.wait_for_timeout(10_000)
        page.click(SEARCH_BUTTON)
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        try:
            page.wait_for_selector("[data-testid='bwsfe-itinerary-list']", timeout=50000)
            return
        except Exception:
            if _is_search_button_loading(page):
                if attempt == 0:
                    continue
                raise Exception("Search button stuck in loading state after refill and retry")
            raise Exception("Itinerary list not found after search")


def _find_booking_response(xhrs: list[dict]) -> dict:
    """Return the first GraphQL SearchResultAvailableOffersQuery response."""
    for xhr in xhrs:
        if GQL_BOOKING_OP in xhr["url"] and xhr["payload"]:
            return xhr["payload"]
    raise ValueError(
        f"availableOffers not found in any collected XHR ({len(xhrs)} responses captured)"
    )

def parse_flights(response: dict) -> List[Flight]:
    offers = response["data"]["availableOffers"]
    results = []

    for it in offers["offerItineraries"]:
        active = it["activeConnection"]
        segs = active["segments"]
        first, last = segs[0], segs[-1]

        # get economy product info
        economy = next(
            (c for p in it.get("upsellCabinProducts", [])
             for c in p["connections"]
             if c.get("cabinClass") == "ECONOMY" and c["price"]["amount"]),
            {}
        )

        layovers = [
            {
                "airport": segs[i]["destination"]["code"],
                "duration_minutes": segs[i].get("transferDuration"),
            }
            for i in range(len(segs) - 1)
        ]

        # airport change warning (e.g. land KIX, depart ITM)
        warnings = [
            w.get("city") for w in active.get("warnings", [])
            if w.get("__typename") == "OfferStationChangeWarning"
        ]

        results.append({
            "airline": active["operatingCarriers"][0]["name"],
            "flight_number": f"{first['marketingFlight']['carrier']['code']} {first['marketingFlight']['number']}",
            "departure_time": first["departureDateTime"][11:16],
            "departure_airport": first["origin"]["code"],
            "arrival_time": last["arrivalDateTime"][11:16],
            "arrival_airport": last["destination"]["code"],
            "arrives_next_days": active.get("dateVariation", 0),  # +1 means next day
            "duration_minutes": active["duration"],
            "stops": 0 if active["isDirect"] else len(segs) - 1,
            "layovers": layovers,
            "price": str(economy.get("price", {}).get("amount")),
            "currency": "EUR",
            "cabin_class": "economy",
            "seats_available": economy.get("numberOfSeatsAvailable"),
            "is_promo": economy.get("isPromo", False),
            "promo_title": economy.get("promoTitle"),
            "has_special_fare": economy.get("hasSpecialFare", False),
            "seat_map_eligible": first.get("seatMapEligible", False),
            "plane_model": first["equipmentName"],
            "co2_kg": offers["searchMetadata"]["environmentalInformation"]["co2InKg"],
            "airport_change_warning": warnings if warnings else None,
        })

    return results


def scrape_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str,
) -> List[Flight]:
    """Scrape flight offers from Air France search GraphQL XHR."""
    p, browser, page = open_session()
    xhr_list, on_response = _start_xhr_collector(page)
    try:
        page.goto(LANDING_URL, wait_until="domcontentloaded", timeout=90_000)
        _fill_search_form(page, origin, destination, departure_date, return_date)
    finally:
        page.remove_listener("response", on_response)
        browser.close()
    response = _find_booking_response(xhr_list)
    return parse_flights(response)
