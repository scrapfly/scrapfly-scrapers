"""
This is an example web scraper for LoopNet.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import json
import re
from typing import Dict, List, Optional, TypedDict
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse, ScrapflyScrapeError


SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "unblocker": True,
    "country": "US",
}

class LoopnetBroker(TypedDict):
    name: Optional[str]
    company: Optional[str]
    phone: Optional[str]
    profile_url: Optional[str]


class LoopnetListing(TypedDict):
    id: Optional[str]
    name: str
    url: str
    description: Optional[str]
    price: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    property_type: Optional[str]
    property_subtype: Optional[str]
    images: List[str]
    video_url: Optional[str]
    broker: Optional[LoopnetBroker]
    details: Dict[str, str]


class LoopnetSearchResult(TypedDict):
    id: Optional[str]
    name: Optional[str]
    url: str
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    price: Optional[str]
    property_type: Optional[str]
    listing_type: Optional[str]
    image: Optional[str]
    data_points: List[str]


class SearchResult(TypedDict):
    total_pages: int
    data: List[LoopnetSearchResult]

def _parse_listing_ld(sel) -> Dict:
    for script in sel.css('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.css("::text").get() or "{}")
        except json.JSONDecodeError:
            continue
        types = data.get("@type")
        if isinstance(types, str):
            types = [types]
        if isinstance(types, list) and "RealEstateListing" in types:
            return data
    return {}


def parse_listing(response: ScrapeApiResponse) -> LoopnetListing:
    sel = response.selector
    listing_ld = _parse_listing_ld(sel)

    details: Dict[str, str] = {}
    for prop in listing_ld.get("additionalProperty", []) or []:
        name = prop.get("name")
        value = prop.get("value")
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        if name and value is not None:
            details[name] = str(value)

    address = (listing_ld.get("contentLocation") or {}).get("address", {}) or {}
    providers = listing_ld.get("provider") or []
    agent = providers[0] if providers else {}
    broker = None
    if agent:
        phone = sel.css("a.number .phone-number::text").get()
        broker = LoopnetBroker(
            name=agent.get("name"),
            company=(agent.get("memberOf") or {}).get("name"),
            phone=phone.strip() if phone else None,
            profile_url=agent.get("@id"),
        )

    images = []
    for img_url in sel.css("section.carousel-wrapper img::attr(src), section.carousel-wrapper img::attr(lazy-src)").getall():
        if img_url and "images1.loopnet.com" in img_url and img_url not in images:
            images.append(img_url)

    videos = listing_ld.get("video") or []
    video_url = videos[0].get("embedUrl") if videos else None

    listing_id_match = re.search(r"/(\d+)/?$", response.context["url"])

    return LoopnetListing(
        id=listing_id_match.group(1) if listing_id_match else None,
        name=listing_ld.get("name", ""),
        url=listing_ld.get("url", response.context["url"]),
        description=listing_ld.get("description"),
        price=details.get("Price"),
        address=address.get("streetAddress"),
        city=address.get("addressLocality"),
        state=address.get("addressRegion"),
        zip_code=address.get("postalCode"),
        property_type=details.get("Property Type"),
        property_subtype=details.get("Property Subtype"),
        images=images,
        video_url=video_url,
        broker=broker,
        details=details,
    )


async def scrape_listings(urls: List[str]) -> List[LoopnetListing]:
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    listings = []
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        if isinstance(result, ScrapflyScrapeError):
            log.error("scrape failed, skipping")
            continue
        try:
            log.info("parsing listing {}", result.context["url"])
            listings.append(parse_listing(result))
        except Exception as e:
            log.error(f"failed to parse listing: {e}")
            continue
    log.success(f"scraped {len(listings)} listings")
    return listings


def _get_total_pages(response: ScrapeApiResponse) -> int:
    # the page numbers are the data-page attributes of the pagination links (nav.pagination)
    pages = [
        int(pg)
        for pg in response.selector.css("nav.pagination a.pagination__page::attr(data-page)").getall()
        if pg.isdigit()
    ]
    return max(pages) if pages else 1


def parse_search(response: ScrapeApiResponse) -> List[LoopnetSearchResult]:
    sel = response.selector
    results = []
    # every listing is an article.placard-card with the listing id in data-lk and the
    # location and type details in its data-automation-* attributes
    for card in sel.css("article.placard-card[data-lk]"):
        name = card.css(".building-name::text").get()
        street = card.css(".placard-address::text").get() or name
        # the card details are rows of spans (type and price, then size and lots or year);
        # the price is the span that starts with "$" (the others say e.g. "Price Upon Request")
        data_points = [dp.strip() for dp in card.css(".placard-data .data-row span:not(.data-sep)::text").getall()]
        data_points = [dp for dp in data_points if dp]
        price = next((dp for dp in data_points if dp.startswith("$")), None)

        results.append(
            LoopnetSearchResult(
                id=card.attrib.get("data-lk"),
                name=name.strip() if name else None,
                url=card.css("a.placard-link::attr(href)").get(""),
                address=street.strip() if street else None,
                city=card.attrib.get("data-automation-city") or None,
                state=card.attrib.get("data-automation-state") or None,
                zip_code=card.attrib.get("data-automation-postal-code") or None,
                price=price,
                property_type=card.attrib.get("data-automation-property-type") or None,
                listing_type=card.attrib.get("data-automation-listing-type") or None,
                image=card.css("img.embla__slide__img::attr(src)").get(),
                data_points=data_points,
            )
        )

    return results


async def scrape_search(search_url: str, max_pages: int = 3) -> SearchResult:
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(search_url, **BASE_CONFIG))
    results = parse_search(first_page)
    if not results and not first_page.selector.css(".search-placards-container"):
        # neither a listing nor the results container: not a search results page, say what came back
        title = (first_page.selector.css("title::text").get() or "").strip()
        raise ValueError(
            f"loopnet.com did not return a search results page for {search_url}: "
            f"got '{title}' at {first_page.context['url']}"
        )
    total_pages = _get_total_pages(first_page)
    pages_to_scrape = min(total_pages, max_pages)

    base_url = search_url.rstrip("/")
    to_scrape = [ScrapeConfig(f"{base_url}/{page}/", **BASE_CONFIG) for page in range(2, pages_to_scrape + 1)]

    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        if isinstance(result, ScrapflyScrapeError):
            log.error("scrape failed, skipping page")
            continue
        try:
            results.extend(parse_search(result))
        except Exception as e:
            log.error(f"failed to parse search page: {e}")
            continue

    log.success(f"scraped {len(results)} results")
    return {"total_pages": total_pages, "data": results}
