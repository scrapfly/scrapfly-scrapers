"""
This is an example web scraper for marriott.com hotel prices and availability.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, TypedDict
from urllib.parse import urlencode

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "render_js": True,
    "country": "US",
    "proxy_pool": "public_residential_pool",
}

_SEARCH_XHR = "phoenixShopDatedSearchByDestinationQuery"
_HQV_URL = "https://www.marriott.com/mi/query/phoenixShopHQVPropertyInfoCall"
_HQV_OP = "phoenixShopHQVPropertyInfoCall"
_HQV_HEADERS = {
    "content-type": "application/json",
    "apollographql-client-name": "phoenix_shop",
    "apollographql-client-version": "v1",
    "graphql-operation-name": _HQV_OP,
    "graphql-require-safelisting": "true",
}

# required header for the graphql call
_OPERATION_SIGNATURES: Dict[str, str] = {}

_HQV_QUERY = """
query phoenixShopHQVPropertyInfoCall($propertyId: ID!, $filter: [ContactNumberType], $descriptionsFilter: [PropertyDescriptionType]) {
  property(id: $propertyId) {
    id
    basicInformation {
      name currency latitude longitude bookable
      brand { name }
      descriptions(filter: $descriptionsFilter) { text type { enumCode } }
    }
    contactInformation {
      address { line1 city postalCode stateProvince { code description } country { code description } }
      contactNumbers(filter: $filter) { phoneNumber { display } }
    }
    reviews { stars { count } numberOfReviews { count } }
    parking { description fees { fee description } }
    policies {
      checkInTime checkOutTime smokefree petsAllowed petsPolicyDescription
      petsPolicyDetails { nonRefundableFee nonRefundableFeeType }
    }
    airports { id name url complimentaryShuttle distanceDetails { description } }
    ... on Hotel { seoNickname }
  }
}
"""


class MarriottProperty(TypedDict):
    marriott_id: str
    name: str
    url: str
    brand: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    distance_meters: Optional[float]
    description: Optional[str]
    review_rating: Optional[float]
    review_count: Optional[int]
    thumbnail: Optional[str]
    bookable: Optional[bool]
    currency: Optional[str]
    lead_price: Optional[str]


class MarriottHotel(TypedDict):
    marriott_id: str
    name: Optional[str]
    url: Optional[str]
    brand: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    currency: Optional[str]
    bookable: Optional[bool]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    country: Optional[str]
    phone: Optional[str]
    description: Optional[str]
    check_in: Optional[str]
    check_out: Optional[str]
    smoke_free: Optional[bool]
    pets_allowed: Optional[bool]
    pets_policy: Optional[str]
    parking: Optional[List[str]]
    review_rating: Optional[float]
    review_count: Optional[int]
    airports: Optional[List[Dict]]


def _build_search_url(city: str, from_date: str, to_date: str, num_rooms: int = 1, num_adults: int = 2) -> str:
    def fmt(d):
        parsed = datetime.strptime(d, "%Y-%m-%d")
        if parsed.date() < datetime.now().date():
            raise ValueError(f"date {d} is in the past")
        return parsed.strftime("%m/%d/%Y")

    return "https://www.marriott.com/search/findHotels.mi?" + urlencode({
        "searchType": "InCity",
        "destinationAddress.destination": city,
        "fromDate": fmt(from_date),
        "toDate": fmt(to_date),
        "numberOfRooms": num_rooms,
        "numAdultsPerRoom": num_adults,
    })


def _parse_operation_signatures(html: str) -> Dict[str, str]:
    """parse the GraphQL operation safelist from page __NEXT_DATA__"""

    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)</script>', html)
    if not match:
        return {}
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}

    signatures = (data.get("props", {}).get("pageProps", {}) or {}).get("operationSignatures") or []
    return {
        item["operationName"]: item["signature"]
        for item in signatures
        if isinstance(item, dict) and item.get("operationName") and item.get("signature")
    }


async def _get_operation_signature(operation: str) -> str:
    """resolve an operation's safelist signature, fetching a search page to harvest it if not cached"""

    if operation not in _OPERATION_SIGNATURES:
        from_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        to_date = (datetime.now() + timedelta(days=32)).strftime("%Y-%m-%d")
        url = _build_search_url("New York", from_date, to_date)
        log.info("fetching operation signatures from {}", url)

        response = await SCRAPFLY.async_scrape(
            ScrapeConfig(url, asp=True, country="US", proxy_pool="public_residential_pool")
        )
        _OPERATION_SIGNATURES.update(_parse_operation_signatures(response.content))

    if operation not in _OPERATION_SIGNATURES:
        raise RuntimeError(f"operation signature for '{operation}' not found in page data")

    return _OPERATION_SIGNATURES[operation]


def parse_search(data: Dict) -> List[MarriottProperty]:
    """Parse property list from dated-search GraphQL payload."""
    edges = data["data"]["search"]["lowestAvailableRates"]["searchByDestination"]["edges"]
    results = []
    for edge in edges:
        node, prop = edge["node"], edge["node"]["property"]
        basic, reviews, rates = prop.get("basicInformation") or {}, prop.get("reviews") or {}, node.get("rates") or []
        descriptions = basic.get("descriptions") or []
        media = ((prop.get("media") or {}).get("primaryImage") or {}).get("edges") or []
        image_urls = (media[0]["node"].get("imageUrls") or {}) if media else {}
        image = image_urls.get("wideHorizontal") or image_urls.get("classicHorizontal")
        if image and image.startswith("//"):
            image = f"https:{image}"
        elif image and image.startswith("/"):
            image = f"https://cache.marriott.com{image}"
        amount = (rates[0]["rateModes"]["lowestAverageRate"].get("amount") or {}) if rates else {}
        lead_price = (
            f"{amount['amount'] / (10 ** amount.get('decimalPoint', 2)):.2f}"
            if amount.get("amount") is not None else None
        )
        results.append({
            "marriott_id": prop["id"],
            "name": basic.get("name"),
            "url": f"https://www.marriott.com/en-us/hotels/{prop['seoNickname']}/overview/",
            "brand": (basic.get("brand") or {}).get("name"),
            "latitude": basic.get("latitude"),
            "longitude": basic.get("longitude"),
            "distance_meters": node.get("distance"),
            "description": next(
                (d.get("text") for d in descriptions if (d.get("type") or {}).get("code") == "HOTEL MARKETING CAPTION"),
                descriptions[0].get("text") if descriptions else None,
            ),
            "review_rating": (reviews.get("stars") or {}).get("count"),
            "review_count": (reviews.get("numberOfReviews") or {}).get("count"),
            "thumbnail": image,
            "bookable": basic.get("bookable"),
            "currency": basic.get("currency"),
            "lead_price": lead_price,
        })
    return results


def parse_hotel(data: Dict) -> MarriottHotel:
    """Parse hotel detail from HQV GraphQL response."""
    prop = data["data"]["property"]
    basic = prop.get("basicInformation") or {}
    contact = prop.get("contactInformation") or {}
    policies = prop.get("policies") or {}
    reviews = prop.get("reviews") or {}
    addr = contact.get("address") or {}
    phones = contact.get("contactNumbers") or []
    descriptions = basic.get("descriptions") or []

    parking = []
    for item in prop.get("parking") or []:
        text = item.get("description") or (item.get("fees") or {}).get("description") or (item.get("fees") or {}).get("fee")
        if text:
            parking.append(text)

    airports = []
    for a in prop.get("airports") or []:
        airports.append({
            "id": a.get("id"),
            "name": a.get("name"),
            "distance": (a.get("distanceDetails") or {}).get("description"),
            "url": a.get("url"),
            "complimentary_shuttle": a.get("complimentaryShuttle"),
        })

    return {
        "marriott_id": prop["id"],
        "name": basic.get("name"),
        "url": f"https://www.marriott.com/en-us/hotels/{prop['seoNickname']}/overview/" if prop.get("seoNickname") else None,
        "brand": (basic.get("brand") or {}).get("name"),
        "latitude": basic.get("latitude"),
        "longitude": basic.get("longitude"),
        "currency": basic.get("currency"),
        "bookable": basic.get("bookable"),
        "address": addr.get("line1"),
        "city": addr.get("city"),
        "state": (addr.get("stateProvince") or {}).get("code"),
        "postal_code": addr.get("postalCode"),
        "country": (addr.get("country") or {}).get("code"),
        "phone": (phones[0].get("phoneNumber") or {}).get("display") if phones else None,
        "description": descriptions[0].get("text") if descriptions else None,
        "check_in": policies.get("checkInTime"),
        "check_out": policies.get("checkOutTime"),
        "smoke_free": policies.get("smokefree"),
        "pets_allowed": policies.get("petsAllowed"),
        "pets_policy": policies.get("petsPolicyDescription") or None,
        "parking": parking,
        "review_rating": (reviews.get("stars") or {}).get("count"),
        "review_count": (reviews.get("numberOfReviews") or {}).get("count"),
        "airports": airports,
    }


async def scrape_search(
    city: str, from_date: str, to_date: str, num_rooms: int = 1, num_adults: int = 2
) -> List[MarriottProperty]:
    """Scrape Marriott city search for the property list."""
    url = _build_search_url(city, from_date, to_date, num_rooms, num_adults)
    log.info("scraping search {}", url)
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, **BASE_CONFIG, wait_for_selector=f"xhr:{_SEARCH_XHR}")
    )
    _OPERATION_SIGNATURES.update(_parse_operation_signatures(response.content))
    xhr_calls = response.scrape_result.get("browser_data", {}).get("xhr_call", [])
    call = next((c for c in xhr_calls if _SEARCH_XHR in c.get("url", "")), None)
    if not call:
        raise RuntimeError(f"XHR call for '{_SEARCH_XHR}' not found")
    results = parse_search(json.loads(call["response"]["body"]))
    log.success("scraped {} properties", len(results))
    return results


async def scrape_hotels(property_ids: List[str]) -> List[MarriottHotel]:
    """Scrape hotel details for the given Marriott property ids."""
    log.info("scraping hotel details for {} properties", len(property_ids))
    signature = await _get_operation_signature(_HQV_OP)
    headers = {**_HQV_HEADERS, "graphql-operation-signature": signature}
    to_scrape = [
        ScrapeConfig(
            _HQV_URL,
            method="POST",
            headers=headers,
            body=json.dumps({
                "operationName": _HQV_OP,
                "query": _HQV_QUERY,
                "variables": {"propertyId": pid, "filter": "PHONE", "descriptionsFilter": ["LOCATION"]},
            }),
            asp=True,
            country="US",
            proxy_pool="public_residential_pool",
        )
        for pid in property_ids
    ]
    results = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        results.append(parse_hotel(json.loads(response.content)))
    log.success("scraped {} hotel details", len(results))
    return results
