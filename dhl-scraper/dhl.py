"""
This is an example web scraper for DHL shipment tracking.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import json
import os
from typing import List, Literal, Optional, TypedDict

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "render_js": True,
    "proxy_pool": "public_residential_pool",
}

API_BASE_URL = "https://www.dhl.com/utapi"
TRACKING_PAGE_URL = "https://www.dhl.com/us-en/home/tracking.html"

Classification = Literal["success", "empty", "captcha-or-forbidden", "semantic-mismatch"]


class TrackingEvent(TypedDict):
    timestamp: Optional[str]
    status: Optional[str]
    description: Optional[str]
    location: Optional[str]


class TrackingResult(TypedDict):
    classification: Classification
    tracking_number: str
    status: Optional[str]
    events: List[TrackingEvent]
    estimated_delivery: Optional[str]
    origin: Optional[str]
    destination: Optional[str]


def _build_tracking_url(tracking_number: str, api_endpoint: bool = False) -> str:
    if api_endpoint:
        return f"{API_BASE_URL}?trackingNumber={tracking_number}"
    return f"{TRACKING_PAGE_URL}?tracking-id={tracking_number}&submit=1"


def _get_xhr_data(response: ScrapeApiResponse, url_pattern: str) -> dict:
    """Extract and parse the JSON body of the first XHR call whose URL contains url_pattern."""
    xhr_calls = response.scrape_result.get("browser_data", {}).get("xhr_call", [])
    call = next((c for c in xhr_calls if url_pattern in c.get("url", "")), None)
    if not call:
        raise RuntimeError(f"XHR call matching '{url_pattern}' not found — try increasing rendering_wait")
    return json.loads(call["response"]["body"])


def _parse_tracking_api_response(data: dict, tracking_number: str) -> TrackingResult:
    shipment = (data.get("shipments") or [None])[0]

    if not shipment:
        return {}

    status = shipment.get("status") or {}
    details = shipment.get("details") or {}
    routes = details.get("dgf:routes") or []

    events = []
    for event in shipment.get("events") or []:
        address = (event.get("location") or {}).get("address") or {}
        events.append(
            {
                "timestamp": event.get("timestamp"),
                "status": event.get("statusCode") or event.get("status"),
                "description": event.get("description"),
                "location": address.get("addressLocality"),
            }
        )

    origin = (shipment.get("origin") or {}).get("address") or {}
    destination = (shipment.get("destination") or {}).get("address") or {}

    return {
        "classification": "success",
        "tracking_number": shipment.get("id") or tracking_number,
        "status": status.get("description") or status.get("statusCode"),
        "events": events,
        "retrieved_at": None,
        "estimated_delivery": routes[0].get("dgf:estimatedArrivalDate") if routes else None,
        "origin": origin.get("addressLocality"),
        "destination": destination.get("addressLocality"),
    }


async def scrape_tracking(tracking_number: str) -> TrackingResult:
    try:
        url = _build_tracking_url(tracking_number, api_endpoint=True)
        response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
        result = _parse_tracking_api_response(json.loads(response.content), tracking_number)
        if result.get("events"):
            return result
    except ScrapflyScrapeError as e:
        log.warning(f"API failed for {tracking_number}: {e}")

    url = _build_tracking_url(tracking_number, api_endpoint=False)
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, wait_for_selector="xhr:/utapi", **BASE_CONFIG)
    )
    data = _get_xhr_data(response, "/utapi")
    log.success("scraped tracking details for {}", tracking_number)
    return _parse_tracking_api_response(data, tracking_number)
