"""
This is an example web scraper for imovelweb.com.br.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
import re
from pathlib import Path
from loguru import logger as log
from typing import List, Dict, TypedDict, Optional
from urllib.parse import urlencode, urlparse, parse_qs
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "proxy_pool": "public_residential_pool",
    "render_js": True,
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

class Location(TypedDict, total=False):
    street: str
    number: str
    postal_code: str
    locality: str
    city: str
    district: str
    province: str
    country: str
    latitude: float
    longitude: float


class PriceInfo(TypedDict, total=False):
    price: float
    price_display: str
    monthly_rental_price: float
    monthly_rental_costs: float


class Agency(TypedDict, total=False):
    name: str
    email: str
    phone: str
    logo: str
    website: str


class PropertyFeatures(TypedDict, total=False):
    bedrooms: int
    bathrooms: int
    room_count: int
    net_habitable_surface: float
    has_lift: bool
    has_terrace: bool
    has_garden: bool
    has_parking: int
    is_furnished: bool


class PropertyResult(TypedDict, total=False):
    """property result item"""
    # IDs
    id: int
    external_reference: str
    link: str
    type: str
    subtype: str
    # Nested structures
    location: Location
    price: PriceInfo
    features: PropertyFeatures
    agency: Agency
    # Media
    images: List[str]
    image_count: int
    # Dates
    creation_date: str
    last_modified: str


class SearchResult(TypedDict):
    """search result item"""
    pass


def parse_property(result: ScrapeApiResponse) -> Dict:
    """Parse detailed property data from imovelweb property page"""
    classified_data = None
    script_content = result.selector.xpath("//script[contains(text(), 'window.classified')]/text()").get()
    if script_content:
        # Extract JSON from: window.classified = {...};
        match = re.search(r"window\.classified\s*=\s*({.*?});", script_content, re.DOTALL)
        if match:
            classified_data = json.loads(match.group(1))

    if not classified_data:
        return {}  # Fallback method HTML parsing
    
    # you can return classified_data directly if you want to see the raw data (more context)
    prop = classified_data.get("property", {})
    loc = prop.get("location", {})
    trans = classified_data.get("transaction", {})
    rental = trans.get("rental", {})
    price_info = classified_data.get("price", {})
    media = classified_data.get("media", {})
    stats = classified_data.get("statistics", {})
    pub = classified_data.get("publication", {})
    certs = trans.get("certificates", {})
    customers = classified_data.get("customers", [])
    customer = customers[0] if customers else {}

    return {
        # IDs
        "id": classified_data.get("id"),
        "external_reference": classified_data.get("externalReference"),
        # Basic property info
        "type": prop.get("type"),
        "subtype": prop.get("subtype"),
        "link": classified_data.get("id")
        and f"https://www.immoweb.be/en/classified/{classified_data['id']}",
        # Price
        "price": price_info.get("mainValue"),
        "price_display": price_info.get("mainDisplayPrice"),
        # Location
        "street": loc.get("street"),
        "number": loc.get("number"),
        "postal_code": loc.get("postalCode"),
        "locality": loc.get("locality"),
        "city": loc.get("locality"),
        "district": loc.get("district"),
        "province": loc.get("province"),
        "country": loc.get("country"),
        "latitude": loc.get("latitude"),
        "longitude": loc.get("longitude"),
        # Rental info
        "monthly_rental_price": rental.get("monthlyRentalPrice"),
        "monthly_rental_costs": rental.get("monthlyRentalCosts"),
        "is_furnished": rental.get("isFurnished"),
        # Rooms & Surface
        "bedrooms": prop.get("bedroomCount", 0),
        "bathrooms": prop.get("bathroomCount"),
        "room_count": prop.get("roomCount"),
        "net_habitable_surface": prop.get("netHabitableSurface"),
        # Features
        "has_lift": prop.get("hasLift"),
        "has_terrace": prop.get("hasTerrace"),
        "has_garden": prop.get("hasGarden"),
        "has_parking": prop.get("parkingCountIndoor")
        or prop.get("parkingCountOutdoor"),
        # Media
        "images": [pic.get("largeUrl") for pic in media.get("pictures", [])],
        "image_count": len(media.get("pictures", [])),
        # Statistics
        "view_count": stats.get("viewCount"),
        "bookmark_count": stats.get("bookmarkCount"),
        # Publication
        "creation_date": pub.get("creationDate"),
        "last_modified": pub.get("lastModificationDate"),
        # Energy & Certificates
        "epc_score": certs.get("epcScore"),
        "energy_class": certs.get("primaryEnergyConsumptionLevel"),
        # Agency/Customer
        "agency_name": customer.get("name"),
        "agency_email": customer.get("email"),
        "agency_phone": customer.get("phoneNumber"),
        "agency_logo": customer.get("logoUrl"),
        "agency_website": customer.get("website"),
    }

async def scrape_properties(urls: List[str]) -> List[PropertyResult]:
    """Scrape detailed property data from imovelweb property pages"""
    log.info(f"Scraping {len(urls)} property pages")

    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    properties = []

    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            properties.append(parse_property(result))
        except Exception as e:
            log.error(f"Error parsing property page {result.context.get('url')}: {e}")
            continue

    log.success(f"Scraped {len(properties)} properties from property pages")
    return properties