"""
This is an example web scraper for Realtor.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-realtorcom/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
import math
import os
import re
import jmespath

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger as log
from parsel import Selector
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # realtor.com requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "country": "US",
}


def parse_property(result: ScrapeApiResponse) -> Dict:
    """
    Parse realtor.com's property page for property data
    and reduce realtor.com's dataset into a cleaner version.
    """
    log.debug("parsing property page: {}", result.context["url"])
    data = result.selector.css("script#__NEXT_DATA__::text").get()
    if not data:
        print(f"page {result.context['url']} is not a property listing page")
        return
    data = json.loads(data)
    raw_data = data["props"]["pageProps"]["initialReduxState"]
    reduced = jmespath.search(
        """{
        id: propertyDetails.listing_id,
        slug: slug,
        url: propertyDetails.href,
        status: propertyDetails.status,
        tags: propertyDetails.tags_for_display[].label,
        sold_date: propertyDetails.last_sold_date,
        sold_price: propertyDetails.last_sold_price,
        list_date: propertyDetails.list_date,
        list_price: propertyDetails.list_price,
        list_price_last_change: propertyDetails.last_price_change_amount,
        details: propertyDetails.description,
        flags: propertyDetails.flags,
        local: propertyDetails.local,
        location: propertyDetails.location,
        agent: propertyDetails.source.agents,
        advertisers: propertyDetails.advertisers,
        tax_history: propertyDetails.tax_history,
        history: propertyDetails.property_history[].{
            date: date,
            event: event_name,
            price: price,
            price_sqft: price_sqft
        },
        photos: propertyDetails.photos[].{
            url: href,
            tags: tags[].label
        },
        phones: propertyDetails.lead_attributes.opcity_lead_attributes.phones[].{
            type: category,
            number: number
        },
        features: propertyDetails.details[].{
            name: category,
            values: text
        }
    }""",
        raw_data,
    )
    reduced['features'] = {feature['name']: feature['values'] for feature in reduced['features']}
    return reduced


async def scrape_property(url: str) -> List[Dict]:
    """scrape realtor.com's property page for property data"""
    log.info("scraping {} property page", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url=url, **BASE_CONFIG))
    property = parse_property(result)
    return property


def _parse_search_card_meta(result: ScrapeApiResponse) -> Dict[str, Dict]:
    """extract metadata from rendered property cards"""
    def _to_int(v):
        if v is None:
            return None
        v = re.sub(r"[^\d]", "", v)
        return int(v) if v else None

    meta_by_permalink: Dict[str, Dict] = {}
    for card in result.selector.xpath("//article[.//a[contains(@href,'/realestateandhomes-detail/')]]"):
        href = card.xpath(".//a[contains(@href,'/realestateandhomes-detail/')]/@href").get() or ""
        m = re.search(r"/realestateandhomes-detail/([^?#]+)", href)
        if not m:
            continue
        permalink = m.group(1)
        meta_by_permalink[permalink] = {
            "beds": _to_int(card.css('[data-testid="property-meta-beds"] [data-testid="meta-value"]::text').get()),
            "baths": _to_int(card.css('[data-testid="property-meta-baths"] [data-testid="meta-value"]::text').get()),
            "sqft": _to_int(card.css('[data-testid="property-meta-sqft"] [data-testid="meta-value"]::text').get()),
            "lot_size": _to_int(card.css('[data-testid="property-meta-lot-size"] [data-testid="meta-value"]::text').get()),
        }
    return meta_by_permalink


def parse_search(result: ScrapeApiResponse) -> Dict:
    """parse realtor.com's search page for search result data"""
    log.info("parsing search page: {}", result.context["url"])

    total_text = result.selector.css("[data-testid='total-results']::text").get("0")
    total_properties = int(total_text.replace(",", "").strip() or "0")
    empty = {"properties": [], "totalProperties": 0}

    # Primary: __NEXT_DATA__ embedded JSON
    next_data = result.selector.css("script#__NEXT_DATA__::text").get()
    if next_data:
        page_props = json.loads(next_data).get("props", {}).get("pageProps", {})
        if "properties" in page_props:
            return {"properties": page_props["properties"], "totalProperties": total_properties}
        log.warning("__NEXT_DATA__ present but missing 'properties' key; falling back to ld+json")

    # Fallback: ld+json structured data
    ld_text = result.selector.css("script[type='application/ld+json']::text").get()
    if not ld_text:
        log.warning("no data source found on search page: {}", result.context["url"])
        return empty

    try:
        ld_data = json.loads(ld_text)
    except json.JSONDecodeError:
        log.warning("failed to parse ld+json on page: {}", result.context["url"])
        return empty

    if not isinstance(ld_data, list):
        ld_data = [ld_data]

    collection = next(
        (item for item in ld_data if isinstance(item, dict) and item.get("@type") == "CollectionPage"),
        None,
    )
    if not collection:
        log.warning("no CollectionPage found in ld+json")
        return empty

    items = collection.get("mainEntity", {}).get("itemListElement", [])
    if not items:
        log.warning("no itemListElement found in CollectionPage mainEntity")
        return empty

    card_meta = _parse_search_card_meta(result)

    properties = []
    for item in items:
        url = item.get("url", "")
        permalink_match = re.search(r"/realestateandhomes-detail/([^?#]+)", url)
        permalink = permalink_match.group(1) if permalink_match else ""

        pid_match = re.search(r"_M(\d+)-(\d+)$", permalink)
        property_id = (pid_match.group(1) + pid_match.group(2)) if pid_match else ""

        price_str = item.get("offers", {}).get("price", "")
        try:
            list_price = int(price_str) if price_str else None
        except (ValueError, TypeError):
            list_price = None

        prop_detail = item.get("mainEntity", {})
        address = prop_detail.get("address", {})
        floor_size = prop_detail.get("floorSize", {})
        image = item.get("image", "")

        dom_meta = card_meta.get(permalink, {})
        ld_baths = prop_detail.get("numberOfBathroomsTotal") or None
        ld_sqft = floor_size.get("value") if floor_size else None

        properties.append({
            "property_id": property_id,
            "permalink": permalink,
            "list_price": list_price,
            "photos": [{"href": image}] if image else [],
            "description": {
                "beds": prop_detail.get("numberOfBedrooms") or dom_meta.get("beds"),
                "baths": ld_baths or dom_meta.get("baths"),
                "sqft": ld_sqft or dom_meta.get("sqft"),
                "lot_size": dom_meta.get("lot_size"),
                "type": prop_detail.get("@type"),
            },
            "location": {
                "address": {
                    "city": address.get("addressLocality"),
                    "state": address.get("addressRegion"),
                    "postal_code": address.get("postalCode"),
                    "line": address.get("streetAddress"),
                }
            },
        })

    return {"properties": properties, "totalProperties": total_properties}



async def scrape_search(state: str, city: str, max_pages: Optional[int] = None) -> List[Dict]:
    """scrape realtor.com's search and find properties for given query. Paginate to max pages if provided"""
    log.info("scraping first property search page for {}, {}", city, state)
    first_page = f"https://www.realtor.com/realestateandhomes-search/{city}_{state}/pg-1"
    first_result = await SCRAPFLY.async_scrape(ScrapeConfig(first_page, render_js=True, **BASE_CONFIG))
    first_data = parse_search(first_result)
    results = first_data["properties"]
    # to avoid division by zero issue
    if len(results) == 0:
        log.warning("no properties found for {}, {}", city, state)
        return results

    total_pages = math.ceil(first_data["totalProperties"] / len(results))
    if max_pages and total_pages > max_pages:
        total_pages = max_pages

    log.info("found {} total pages", total_pages)
    to_scrape = []
    for page in range(1, total_pages + 1):
        assert "pg-1" in first_result.context["url"]  # make sure we don't accidently scrape duplicate pages
        page_url = first_result.context["url"].replace("pg-1", f"pg-{page}")
        to_scrape.append(ScrapeConfig(page_url, render_js=True, **BASE_CONFIG))

    log.info("scraping {} property search pages for {}, {}", len(to_scrape), city, state)
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        parsed = parse_search(result)
        results.extend(parsed["properties"])
    log.info(f"scraped search of {len(results)} results for {city}, {state}")
    return results


async def scrape_feed(url) -> Dict[str, datetime]:
    """scrapes atom RSS feed and returns all entries in "url:publish date" format"""
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG, retry=True))
    body = result.content
    selector = Selector(text=body)
    results = {}
    for item in selector.xpath("//sitemap"):
        url = item.xpath("loc/text()").get()
        pub_date = item.xpath("lastmod/text()").get()
        results[url] = datetime.fromisoformat(pub_date)
    return results


async def track_feed(url: str, output: Path, interval=60):
    """Track Realtor.com feed, scrape new listings and append them as JSON to the output file"""
    seen = set()
    output.touch(exist_ok=True)
    try:
        while True:
            changed = await scrape_feed(url=url)
            # check deduplication filter
            changed = {k: v for k, v in changed.items() if f"{k}:{v}" not in seen}
            if changed:
                # scrape properties and save to file - 1 property as JSON per line
                properties = await asyncio.gather(scrape_property(url) for url in changed.keys())
                with output.open("a") as f:
                    f.write("\n".join(json.dumps(property) for property in properties))

                # add seen to deduplication filter
                for k, v in changed.items():
                    seen.add(f"{k}:{v}")
            print(f"scraped {len(properties)} properties; waiting {interval} seconds")
            await asyncio.sleep(interval)
    except KeyboardInterrupt:
        print("stopping price tracking")
