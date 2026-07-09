"""
This is an example web scraper for maersk.com container tracking and schedules.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, TypedDict
from urllib.parse import urlencode

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "render_js": True,
    "rendering_wait": 5000,

}


class VesselInfo(TypedDict):
    name: str
    code: str
    flag_country: str


class PortCall(TypedDict):
    facility_code: str
    geo_id: Optional[str]
    estimated_arrival: Optional[str]
    estimated_departure: Optional[str]
    voyage_number: Optional[str]
    service_name: Optional[str]
    service_code: Optional[str]


class RoutingLeg(TypedDict):
    carriage_type: str
    transport_mode: str
    vessel: Optional[VesselInfo]
    origin: PortCall
    destination: PortCall
    transit_time: Optional[str]


class ScheduleRoute(TypedDict):
    route_id: str
    route_code: str
    route_direction: str
    estimated_transit_time: str
    estimated_transit_days: Optional[int]
    vessel_name: Optional[str]
    origin_facility: Optional[str]
    destination_facility: Optional[str]
    departure_time: Optional[str]
    arrival_time: Optional[str]
    service_name: Optional[str]
    voyage_number: Optional[str]
    legs: List[RoutingLeg]


class ScheduleSearch(TypedDict):
    url: str
    from_rkst_code: str
    to_rkst_code: str
    departure_date: str
    route_count: int
    routes: List[ScheduleRoute]

class TrackingEvent(TypedDict):
    location: Optional[str]
    facility: Optional[str]
    description: str
    date: Optional[str]
    vessel: Optional[str]
    voyage: Optional[str]
    is_current: bool

class TrackingContainer(TypedDict):
    container_number: Optional[str]
    container_type: Optional[str]
    last_updated: Optional[str]
    status: Optional[str]
    current_location: Optional[str]
    status_date: Optional[str]
    events: List[TrackingEvent]


class TrackingResult(TypedDict):
    tracking_number: str
    origin: Optional[str]
    destination: Optional[str]
    containers: List[TrackingContainer]

def _parse_port_call(port_call: Dict) -> PortCall:
    facility = port_call.get("location", {}).get("facility", {})
    service = port_call.get("departureService") or port_call.get("arrivalService") or {}

    geo_id = None
    for code in facility.get("alternativeCodes", []):
        if code.get("alternativeCodeType") == "GEO_ID":
            geo_id = code.get("alternativeCode")
            break

    return PortCall(
        facility_code=facility.get("facilityCode", ""),
        geo_id=geo_id,
        estimated_arrival=port_call.get("estimatedTimeOfArrival"),
        estimated_departure=port_call.get("estimatedTimeOfDeparture"),
        voyage_number=port_call.get("departureVoyageNumber") or port_call.get("arrivalVoyageNumber"),
        service_name=service.get("serviceName"),
        service_code=service.get("serviceCode"),
    )


def _parse_routing(routing: Dict) -> Optional[ScheduleRoute]:
    legs: List[RoutingLeg] = []
    for leg in routing.get("routingLegs", []):
        carriage = leg.get("carriage", {})
        start = carriage.get("vesselPortCallStart")
        end = carriage.get("vesselPortCallEnd")
        if not start or not end:
            continue

        vessel_data = carriage.get("vessel")
        vessel = None
        if vessel_data:
            vessel = VesselInfo(
                name=vessel_data.get("vesselName", ""),
                code=vessel_data.get("vesselMaerskCode", ""),
                flag_country=vessel_data.get("flagCountryCode", ""),
            )

        legs.append(
            RoutingLeg(
                carriage_type=carriage.get("carriageType", ""),
                transport_mode=leg.get("transportMode", {}).get("transportModeCode", ""),
                vessel=vessel,
                origin=_parse_port_call(start),
                destination=_parse_port_call(end),
                transit_time=leg.get("estimatedTransitTime"),
            )
        )

    if not legs:
        return None

    first_leg = legs[0]
    last_leg = legs[-1]
    vessel = first_leg.get("vessel")
    estimated_transit = routing.get("estimatedTransitTime") or ""
    days_match = re.match(r"^P(?:(\d+)D)", estimated_transit)

    return ScheduleRoute(
        route_id=routing.get("routeId", ""),
        route_code=routing.get("routeCode", ""),
        route_direction=routing.get("routeCodeDirection", ""),
        estimated_transit_time=estimated_transit,
        estimated_transit_days=int(days_match.group(1)) if days_match else None,
        vessel_name=vessel["name"] if vessel else None,
        origin_facility=first_leg["origin"]["facility_code"] or None,
        destination_facility=last_leg["destination"]["facility_code"] or None,
        departure_time=first_leg["origin"]["estimated_departure"],
        arrival_time=last_leg["destination"]["estimated_arrival"],
        service_name=first_leg["origin"]["service_name"],
        voyage_number=first_leg["origin"]["voyage_number"],
        legs=legs,
    )


def _get_xhr_data(response: ScrapeApiResponse, url_pattern: str) -> Dict:
    """Extract and parse the JSON body of the first XHR call whose URL contains url_pattern."""
    xhr_calls = response.scrape_result.get("browser_data", {}).get("xhr_call", [])
    call = next((c for c in xhr_calls if url_pattern in c.get("url", "")), None)
    if not call:
        raise RuntimeError(f"XHR call matching '{url_pattern}' not found — try increasing rendering_wait")
    return json.loads(call["response"]["body"])


def parse_schedule_search(
    response: ScrapeApiResponse,
    from_rkst_code: str,
    to_rkst_code: str,
    departure_date: str,
) -> ScheduleSearch:
    """Parse point-to-point schedule results from the routings-queries XHR response."""
    data = _get_xhr_data(response, "routing/routings-queries")
    if "routings" not in data:
        raise RuntimeError("'routings' key missing in routings-queries XHR response")

    routes: List[ScheduleRoute] = []
    for routing in data.get("routings", []):
        parsed_route = _parse_routing(routing)
        if parsed_route:
            routes.append(parsed_route)

    log.success("parsed {} schedule routes {} -> {}", len(routes), from_rkst_code, to_rkst_code)
    return ScheduleSearch(
        url=response.context.get("url", ""),
        from_rkst_code=from_rkst_code,
        to_rkst_code=to_rkst_code,
        departure_date=departure_date,
        route_count=len(routes),
        routes=routes,
    )


def parse_tracking(data: Dict, tracking_number: str) -> TrackingResult:
    """Parse Maersk synergy tracking API JSON into structured tracking data."""
    containers: List[TrackingContainer] = []

    for c in data.get("containers", []):
        locations = c.get("locations", [])
        all_events = [
            (loc, ev)
            for loc in locations
            for ev in loc.get("events", [])
        ]
        events = [
            TrackingEvent(
                location=loc.get("city"),
                facility=loc.get("terminal"),
                description=ev.get("activity", ""),
                date=ev.get("event_time"),
                vessel=ev.get("vessel_name"),
                voyage=ev.get("voyage_num"),
                is_current=(i == len(all_events) - 1),
            )
            for i, (loc, ev) in enumerate(all_events)
        ]

        last_loc = locations[-1] if locations else {}
        containers.append(TrackingContainer(
            container_number=c.get("container_num"),
            container_type=f"{c.get('container_size', '')}' {c.get('container_type', '')}".strip() or None,
            last_updated=c.get("last_update_time"),
            status=c.get("status"),
            current_location=last_loc.get("city"),
            status_date=last_loc.get("events", [{}])[-1].get("event_time"),
            events=events,
        ))

    return TrackingResult(
        tracking_number=tracking_number,
        origin=data.get("origin", {}).get("city"),
        destination=data.get("destination", {}).get("city"),
        containers=containers,
    )


async def scrape_schedule_search(
    from_location: str,
    to_location: str,
    from_rkst_code: str,
    to_rkst_code: str,
    departure_date: str,
) -> ScheduleSearch:
    """Search maersk.com Point-to-Point schedules"""
    date_to = (datetime.strptime(departure_date, "%Y-%m-%d") + timedelta(weeks=4)).strftime("%Y-%m-%d")
    url = "https://www.maersk.com/schedules/pointToPoint?" + urlencode({
        "from": from_location,
        "to": to_location,
        "fromRkstCode": from_rkst_code,
        "toRkstCode": to_rkst_code,
        "date": departure_date,
        "dateTo": date_to,
    })

    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url,
            **BASE_CONFIG,
            wait_for_selector="xhr:routings-queries",
        )
    )
    log.success("searched schedules {} -> {}", from_rkst_code, to_rkst_code)
    return parse_schedule_search(response, from_rkst_code, to_rkst_code, departure_date)


async def scrape_tracking(tracking_number: str) -> TrackingResult:
    """Scrape a container/BL/booking number from maersk.com's tracking widget."""
    url = f"https://www.maersk.com/tracking/{tracking_number}"
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url,
            **BASE_CONFIG,
            wait_for_selector="xhr:synergy/tracking",
        )
    )
    data = _get_xhr_data(response, "synergy/tracking")
    log.success("scraped tracking details for {}", tracking_number)
    return parse_tracking(data, tracking_number)