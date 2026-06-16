"""
This is an example web scraper for kayak.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "proxy_pool": "public_residential_pool",
    "country": "US",
}

POLL_URL = "https://www.kayak.com/i/api/search/dynamic/flights/poll"
SEARCH_RESULTS_SELECTOR = "//div[contains(text(), 'results')]"


def build_search_url(origin, destination, departure_date, return_date=None, sort="bestflight_a"):
    origin, destination = origin.upper(), destination.upper()
    path = f"/flights/{origin}-{destination}/{departure_date}"
    if return_date:
        path += f"/{return_date}"
    return f"https://www.kayak.com{path}?sort={sort}"


def parse_flight_results(
    page_data: Dict[str, Any],
    origin: str,
    destination: str,
    departure_date: str,
    captured_at: str,
) -> List[Dict[str, Any]]:
    trip_type = (page_data.get("searchStatus", {}).get("tripType") or "oneway")
    trip_type = trip_type.lower().replace("roundtrip", "round_trip").replace("oneway", "one_way")
    legs = page_data.get("legs") or {}
    segments = page_data.get("segments") or {}
    airlines = page_data.get("airlines") or {}
    flights = []

    for item in page_data.get("results") or []:
        if item.get("type") != "core":
            continue

        option = (item.get("bookingOptions") or [{}])[0]
        price_info = option.get("displayPrice") or {}
        leg_faring = (option.get("legFarings") or [{}])[0]
        leg = legs.get(leg_faring.get("legId") or "") or {}

        seg_id = ((leg.get("segments") or [{}])[0]).get("id") or ""
        airline_code = segments.get(seg_id, {}).get("airline")
        carrier = (airlines.get(airline_code) or {}).get("name") or airline_code

        dep = (leg_faring.get("approxDepartureTime") or "").replace(" am", " AM").replace(" pm", " PM").strip()
        arr = (leg_faring.get("approxArrivalTime") or "").replace(" am", " AM").replace(" pm", " PM").strip()
        if arr and leg.get("departure") and leg.get("arrival"):
            try:
                if datetime.fromisoformat(leg["arrival"]).date() > datetime.fromisoformat(leg["departure"]).date():
                    arr = f"{arr} +1"
            except ValueError:
                pass

        minutes = leg.get("duration")
        if minutes is not None:
            hours, mins = divmod(int(minutes), 60)
            duration = f"{hours}h {mins:02d}" if hours else f"{mins}m"
        else:
            duration = None

        seg_count = len(leg.get("segments") or [])
        stops = "Direct" if seg_count <= 1 else f"{max(seg_count - 1, 1)} stop{'s' if seg_count > 2 else ''}"

        price = price_info.get("price")
        flights.append({
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "trip_type": trip_type,
            "currency": price_info.get("currency"),
            "carrier": carrier,
            "departure_time": dep or None,
            "arrival_time": arr or None,
            "duration": duration,
            "stops": stops,
            "price": f"${int(price)}" if price is not None else None,
            "provider_deal_count": item.get("totalBookingOptions", 0),
            "captured_at": captured_at,
        })

    return flights


def _build_poll_payload(origin, destination, departure_date, return_date, search_id, sort, page_number):
    legs = [{
        "origin": {"airports": [origin], "locationType": "airports"},
        "destination": {"airports": [destination], "locationType": "airports"},
        "date": departure_date,
        "flex": "exact",
    }]
    if return_date:
        legs.append({
            "origin": {"airports": [destination], "locationType": "airports"},
            "destination": {"airports": [origin], "locationType": "airports"},
            "date": return_date,
            "flex": "exact",
        })
    return {
        "filterParams": {},
        "userSearchParams": {
            "legs": legs,
            "searchId": search_id,
            "passengers": ["ADT"],
            "passengerDetails": [{"ptc": "ADT"}],
            "sortMode": sort,
        },
        "searchMetaData": {"pageNumber": page_number, "searchTypes": []},
    }


def parse_poll_call(response: ScrapeApiResponse):
    """extract poll API call from xhr_calls"""
    _xhr_calls = response.scrape_result["browser_data"]["xhr_call"]
    poll_call = [call for call in _xhr_calls if POLL_URL in call["url"]][-1]
    headers = poll_call["headers"]
    return poll_call, headers


async def scrape_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    sort: str = "bestflight_a",
    max_pages: int = 10,
) -> List[Dict[str, Any]]:
    origin, destination = origin.upper(), destination.upper()
    url = build_search_url(origin, destination, departure_date, return_date, sort)
    log.info(f"scraping kayak {origin}->{destination} on {departure_date}")

    session_id = f"kayak-{uuid4().hex}"
    search_response = await SCRAPFLY.async_scrape(ScrapeConfig(
        url, **BASE_CONFIG, render_js=True, session=session_id,
        rendering_wait=3000, wait_for_selector=SEARCH_RESULTS_SELECTOR,
    ))

    poll_call, poll_headers = parse_poll_call(search_response)
    page_data = json.loads(poll_call["response"]["body"])
    search_id = page_data["searchId"]
    captured_at = datetime.now(timezone.utc).isoformat()

    all_results = parse_flight_results(page_data, origin, destination, departure_date, captured_at)
    filtered_count = page_data.get("filteredCount", 0)
    start_page = page_data.get("pageNumber", 1)
    pages_scraped = 1

    for page_number in range(start_page + 1, start_page + max_pages + 1):
        if len(all_results) >= filtered_count:
            break
        response = await SCRAPFLY.async_scrape(ScrapeConfig(
            POLL_URL, **BASE_CONFIG, session=session_id, method="POST",
            headers=poll_headers,
            body=json.dumps(_build_poll_payload(origin, destination, departure_date, return_date, search_id, sort, page_number)),
            render_js=False,
        ))
        page_data = json.loads(response.content)
        page_results = parse_flight_results(page_data, origin, destination, departure_date, captured_at)
        all_results.extend(page_results)
        pages_scraped += 1
        log.info(f"page {page_number}: +{len(page_results)} (total {len(all_results)}/{filtered_count})")
        if page_data.get("status") == "complete" and not page_results:
            break

    log.success(f"scraped {len(all_results)} flights for {origin}->{destination} across {pages_scraped} pages")
    return all_results
