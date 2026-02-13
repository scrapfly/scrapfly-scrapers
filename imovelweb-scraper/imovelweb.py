"""
This is an example web scraper for imovelweb.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
import re
from pathlib import Path
from loguru import logger as log
from typing import List, Dict, TypedDict
from urllib.parse import urlencode, urlparse
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse, ScrapflyScrapeError

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

    total_pages: int
    total_properties: int
    search_properties: List[Dict]


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
        "link": classified_data.get("id") and f"https://www.immoweb.be/en/classified/{classified_data['id']}",
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
        "has_parking": prop.get("parkingCountIndoor") or prop.get("parkingCountOutdoor"),
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


def parse_search_page(result: ScrapeApiResponse) -> SearchResult:
    """Parse search page data from imovelweb search page"""
    sel = result.selector
    total_properties = 0
    max_pages = 1
    properties = []

    # Check if no results were found
    no_results = sel.css("h1.empty-state__title::text").get()
    if no_results and "no matching results" in no_results.lower():
        log.warning("No matching results found for this search")
        return {
            "total_properties": 0,
            "total_pages": 0,
            "properties": [],
        }

    title = sel.css("h1.search-results__title::text").get()
    if title:
        match = re.search(r"(\d+(?:,\d+)*)\s+propert", title)
        total_properties = int(match.group(1).replace(",", ""))

    # Get all page links from pagination
    max_pages = 1
    page_links = sel.css("ul.pagination li.pagination__item a.pagination__link::attr(href)").getall()
    for link in page_links:
        # Extract page number from URL parameter
        match = re.search(r"[?&]page=(\d+)", link)
        if match:
            page_num = int(match.group(1))
            max_pages = max(max_pages, page_num)

    property_cards = sel.css("article.card--result:not([id*='recommendation'])")

    log.info(f"Found {len(property_cards)} property cards on search page")

    for card in property_cards:
        try:
            # Extract property data from card
            property_id = card.css("::attr(id)").get() or ""
            if property_id:
                property_id = property_id.replace("classified_", "")
            # Extract link
            link = card.css("a::attr(href)").get() or card.xpath(".//a/@href").get()
            if link and not link.startswith("http"):
                root_domain = result.context["uri"][
                    "root_domain"
                ]  # Use actual domain after redirects (e.g., .com -> .br)
                link = f"https://{root_domain}{link}" if link.startswith("/") else f"https://{root_domain}/{link}"

            # Extract price
            currency = ""
            price_min = ""
            price_max = ""
            price_text = card.css("[class*='price'], [data-testid*='price']::text").get()
            if price_text:
                currency_match = re.search(r"([€$£¥]|R\$)", price_text)
                currency = currency_match.group(1) if currency_match else ""

                # Extract numbers
                numbers = re.findall(r"[\d.,]+", price_text)
                clean_numbers = [num.replace(",", "").replace(".", "") for num in numbers]

                price_min = clean_numbers[0] if clean_numbers else ""
                price_max = clean_numbers[1] if len(clean_numbers) > 1 else ""

            # Extract location
            location_text = card.css(
                "p.card__information--locality::text, p.card--results__information--locality::text"
            ).get()

            postal_code = ""
            city = ""
            if location_text:
                location_text = location_text.strip()
                match = re.match(r"(\d+)\s+(.+)", location_text)
                if match:
                    postal_code = match.group(1)
                    city = match.group(2)
                else:
                    city = location_text

            # Extract bedrooms
            bedrooms = ""
            bedrooms_span = card.css(
                "p.card__information--property span.abbreviation span[aria-hidden='true']::text"
            ).get()
            if bedrooms_span:
                bed_match = re.search(r"(\d+)", bedrooms_span)
                if bed_match:
                    bedrooms = bed_match.group(1)

            # Extract area
            area = ""
            area_text = card.css("p.card__information--property::text").getall()
            for text in area_text:
                if text.strip() and text.strip().isdigit():
                    area = f"{text.strip()} m²"
                    break

            # Extract description
            description = card.css("div.card__description::text").get() or ""
            description = description.strip()

            # Extract flags/badges
            flags = []
            flag_items = card.css("div.flag-list__item span.flag-list__text::text").getall()
            flags = [f.strip() for f in flag_items if f.strip()]

            # Extract agency logo
            agency_logo = (
                card.css("img.card--result__agency-logo::attr(src), img.card__logo--large::attr(src)").get() or ""
            )
            agency_name = (
                card.css("img.card--result__agency-logo::attr(alt), img.card__logo--large::attr(alt)").get() or ""
            )

            # Extract images
            images = []
            image_urls = card.css("img.card__media-picture::attr(src)").getall()
            images = [img for img in image_urls if img]

            property_data = {
                "id": property_id,
                "url": link,
                "currency": currency,
                "price_min": price_min,
                "price_max": price_max,
                "postal_code": postal_code,
                "city": city,
                "bedrooms": bedrooms,
                "area": area,
                "description": description,
                "flags": flags,
                "agency_logo": agency_logo,
                "agency_name": agency_name,
                "images": images,
            }
            properties.append(property_data)
        except Exception as e:
            log.error(f"Error parsing property card {card}: {e}")
            continue

    return {
        "total_properties": total_properties,
        "total_pages": max_pages,
        "properties": properties,
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


async def scrape_search(
    query: str = None, for_sale: bool = False, max_pages: int = 3, scrape_all_pages: bool = False, **filters
) -> SearchResult:
    """scrape imovelweb search pages

    Args:
        query (str, optional): search query. Defaults to None.
        for_sale (bool, optional): search for salet. Defaults to False (for rent).
        max_pages (int, optional): maximum number of pages to scrape. Defaults to 3.
        scrape_all_pages (bool, optional): scrape all pages. Defaults to False.
        **filters: search filters (e.g. location, price, etc.)

    Returns:
        List[Dict]: list of properties
    """
    search_properties = []
    base_url = "https://www.immoweb.be/en/search/house-and-apartment"  # using .be as .com redirects and blocks filters

    # Handle for-sale or for-rent
    listing_type = "for-sale" if for_sale else "for-rent"

    query_slug = ""

    if query:
        query_slug = query.lower().replace(" ", "-")

    # Build the URL
    url = f"{base_url}/{listing_type}/{query_slug}".rstrip("/")

    if filters:
        processed_filters = {}
        for key, value in filters.items():
            if isinstance(value, list):
                # Join list items with commas (unencoded)
                processed_filters[key] = ",".join(str(v) for v in value)
            else:
                processed_filters[key] = value

        # Build query string manually to avoid encoding commas
        query_parts = []
        for key, value in processed_filters.items():
            if "," in str(value):
                # Don't encode values with commas
                query_parts.append(f"{key}={value}")
            else:
                # Encode other values normally
                query_parts.append(f"{key}={urlencode({key: value})[len(key)+1:]}")

        url += "?" + "&".join(query_parts)

    log.info(f"Scraping search first page: {url}")

    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    first_page_data = parse_search_page(first_page)
    search_properties = first_page_data["properties"]
    total_properties = first_page_data["total_properties"]
    total_pages = first_page_data["total_pages"]

    if scrape_all_pages:
        pages_to_scrape = total_pages
    else:
        pages_to_scrape = min(max_pages, total_pages)

    scraped_pages = 1
    log.info(f"Scraping {pages_to_scrape - 1} additional pages (total: {pages_to_scrape})")

    if pages_to_scrape > 1:
        separator = "&" if urlparse(url).query else "?"
        other_pages = [
            ScrapeConfig(url + f"{separator}page={page}", **BASE_CONFIG) for page in range(2, pages_to_scrape + 1)
        ]
        async for result in SCRAPFLY.concurrent_scrape(other_pages):
            if isinstance(result, ScrapflyScrapeError):
                log.error(f"ASP protection failed - skipping page {result.context.get('url')}")
                continue
            try:
                page_data = parse_search_page(result)
                search_properties.extend(page_data["properties"])
                scraped_pages += 1
            except Exception as e:
                log.error(f"Error parsing search page {result.context.get('url')}: {e}")
                continue
        log.success(f"scraped properties {len(search_properties)}")
    data = {
        "total_pages": total_pages,
        "total_properties": total_properties,
        "search_properties": search_properties,
    }

    return data
