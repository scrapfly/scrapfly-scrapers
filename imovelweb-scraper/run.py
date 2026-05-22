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
from typing import List, Dict, Optional
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "proxy_pool": "public_residential_pool",
    "render_js": True,
    "country": "BR",
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

_PROPERTY_TYPES = {"Apartment", "House", "SingleFamilyResidence", "RealEstateListing", "Residence", "Accommodation"}


def _parse_jsonld(sel) -> Optional[Dict]:
    """Find the property-specific JSON-LD block, skipping WebSite/Organization entries."""
    for s in sel.xpath("//script[@type='application/ld+json']/text()").getall():
        try:
            data = json.loads(s)
        except json.JSONDecodeError:
            continue
        for item in (data if isinstance(data, list) else [data]):
            if isinstance(item, dict) and item.get("@type") in _PROPERTY_TYPES:
                return item
    return None


def parse_property(result: ScrapeApiResponse) -> Dict:
    """Parse detailed property data from an imovelweb.com.br property page."""
    sel = result.selector
    out: Dict = {"url": result.context["url"], "currency": "BRL"}

    if ld := _parse_jsonld(sel):
        addr = ld.get("address", {})
        parts = [p.strip() for p in (addr.get("addressLocality") or "").strip(" ,").split(",") if p.strip().lower() != "brasil"]
        out.update({
            "description": ld.get("description"),
            "bedrooms": ld.get("numberOfBedrooms"),
            "bathrooms": ld.get("numberOfBathroomsTotal"),
            "area_m2": (ld.get("floorSize") or {}).get("value"),
            "phone": ld.get("telephone"),
            "street": addr.get("streetAddress"),
            "neighborhood": addr.get("addressRegion"),
            "city": parts[0] if parts else None,
            "state": parts[1] if len(parts) > 1 else None,
        })

    h1 = sel.css("h1::text").get("").strip()
    out["title"] = h1 if h1.lower() != "imovelweb" else None

    if m := re.search(r"R\$\s*([\d.]+(?:,\d+)?)", sel.css("title::text").get("")):
        out["price_display"] = f"R$ {m.group(1)}"
        out["price"] = float(m.group(1).replace(".", "").replace(",", "."))

    out["images"] = sel.css("img[src*='imovelwebcdn'][src*='/avisos/']::attr(src)").getall()
    return out


def parse_search_page(result: ScrapeApiResponse) -> Dict:
    """Parse listing cards from an imovelweb.com.br search page."""
    sel = result.selector
    properties = []

    for card in sel.css(".postingCardLayout-module__posting-card-layout"):
        link = card.attrib.get("data-to-posting", "")
        if not link:
            continue
        features = card.css("[data-qa='POSTING_CARD_FEATURES'] span::text").getall()
        properties.append({
            "title": card.css("[data-qa='POSTING_CARD_DESCRIPTION'] a::text").get("").strip() or None,
            "price": card.css("[data-qa='POSTING_CARD_PRICE']::text").get("").strip() or None,
            "area": next((t.strip() for t in features if "m²" in t), None),
            "bedrooms": next((t.strip() for t in features if re.search(r"\bquartos?\b|\bdormitórios?\b", t, re.I)), None),
            "bathrooms": next((t.strip() for t in features if re.search(r"\bbanheiros?\b", t, re.I)), None),
            "url": f"https://www.imovelweb.com.br{link}" if link.startswith("/") else link,
            "thumbnail": card.css(".postingGallery-module__gallery-container img::attr(src)").get(),
        })

    log.info(f"Found {len(properties)} property cards on search page")

    total_properties = len(properties)
    if m := re.search(r"([\d.]+)\s+imóv", " ".join(sel.css("h1::text, [data-qa='results-count']::text").getall()), re.I):
        total_properties = int(m.group(1).replace(".", ""))

    return {"total_properties": total_properties, "properties": properties}


async def scrape_properties(urls: List[str]) -> List[Dict]:
    """Scrape detailed property data from imovelweb.com.br property pages."""
    log.info(f"Scraping {len(urls)} property pages")
    properties = []
    async for result in SCRAPFLY.concurrent_scrape([ScrapeConfig(url, **BASE_CONFIG) for url in urls]):
        try:
            properties.append(parse_property(result))
        except Exception as e:
            log.error(f"Error parsing {result.context.get('url')}: {e}")
    log.success(f"Scraped {len(properties)} properties")
    return properties


async def scrape_search(
    location: str = "sao-paulo-sp",
    property_type: str = "imoveis",
    for_sale: bool = False,
    max_pages: int = 3,
) -> Dict:
    """Scrape imovelweb.com.br search pages."""
    transaction = "venda" if for_sale else "aluguel"
    base_url = f"https://www.imovelweb.com.br/{property_type}-{transaction}-{location}"

    log.info(f"Scraping first page: {base_url}.html")
    first_data = parse_search_page(await SCRAPFLY.async_scrape(ScrapeConfig(f"{base_url}.html", **BASE_CONFIG)))

    all_properties = first_data["properties"]
    total_properties = first_data["total_properties"]

    if max_pages > 1:
        other_pages = [ScrapeConfig(f"{base_url}-pagina-{page}.html", **BASE_CONFIG) for page in range(2, max_pages + 1)]
        async for result in SCRAPFLY.concurrent_scrape(other_pages):
            try:
                all_properties.extend(parse_search_page(result)["properties"])
            except Exception as e:
                log.error(f"Error scraping page: {e}")

    log.success(f"Scraped {len(all_properties)} properties across {max_pages} pages")
    return {"total_properties": total_properties, "total_pages": max_pages, "search_properties": all_properties}
