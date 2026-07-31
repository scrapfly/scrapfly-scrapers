"""
This is an example web scraper for RS-Online (rs-online.com)

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, TypedDict
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "us",
    "proxy_pool": "public_residential_pool",
    "rendering_wait": 5000
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


class RSProduct(TypedDict):
    name: str
    url: str
    rs_stock_number: str
    mpn: Optional[str]
    brand: Optional[str]
    description: Optional[str]
    price: Optional[str]
    currency: Optional[str]
    availability: Optional[str]
    stock_quantity: Optional[int]
    min_order_qty: Optional[int]
    qty_increment: Optional[int]
    tiered_pricing: Optional[Dict[str, float]]
    lead_time_required: Optional[bool]
    datasheet_url: Optional[str]
    image: Optional[str]
    specifications: Dict[str, str]
    compliance: List[str]
    category: Optional[str]


class RSSearchResult(TypedDict):
    name: Optional[str]
    url: Optional[str]
    rs_stock_number: Optional[str]
    mpn: Optional[str]
    price: Optional[str]
    currency: Optional[str]
    availability: Optional[str]
    stock_quantity: Optional[int]
    image: Optional[str]


def _extract_product_json_ld(sel) -> Dict:
    for script in sel.css('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.css("::text").get() or "{}")
        except json.JSONDecodeError:
            continue
        if data.get("@type") == "Product":
            return data
    return {}


def _extract_ga4_item(html: str) -> Dict:
    match = re.search(r"var dl4Objects\s*=\s*(\[.*?\]);\s*\n\s*for", html, re.S)
    if not match:
        return {}
    try:
        dl4_objects = json.loads(match.group(1))
    except json.JSONDecodeError:
        return {}
    for obj in dl4_objects:
        items = obj.get("ecommerce", {}).get("items", [])
        if items:
            return items[0]
    return {}


def parse_product(response: ScrapeApiResponse) -> RSProduct:
    sel = response.selector
    html = response.content

    product_ld = _extract_product_json_ld(sel)
    offers = product_ld.get("offers", {}) or {}
    ga4_item = _extract_ga4_item(html)

    availability = ga4_item.get("item_stock_status") or offers.get("availability", "") or ""
    if availability.startswith("https://schema.org/"):
        availability = availability.replace("https://schema.org/", "")

    rs_stock_number = (sel.css(".product.attribute.sku .value::text").get() or "").strip()
    mpn = "".join(sel.css('[itemprop="manufacturer_part_number"]::text').getall()).strip()

    stock_match = None
    for text in sel.css(".badge-block.stock-status-bg .badge-text ::text").getall():
        stock_match = re.match(r"(.+?)\s*-\s*(\d+)\s*$", text.strip())
        if stock_match:
            break
    stock_quantity = int(stock_match.group(2)) if stock_match else None
    if not availability and stock_match:
        availability = stock_match.group(1)

    min_order_match = re.search(r'"minSaleQty":\s*(\d+)', html)
    qty_increment_match = re.search(r'"qtyIncrements":\s*(\d+)', html)

    tiered_pricing = None
    tier_raw = sel.css("#base-tier-pricing::attr(data-basetierprices)").get()
    if tier_raw:
        try:
            parsed_tiers = json.loads(tier_raw)
        except json.JSONDecodeError:
            parsed_tiers = None
        if isinstance(parsed_tiers, dict) and parsed_tiers:
            tiered_pricing = parsed_tiers

    specifications = {}
    for td in sel.css("td.col.data"):
        label = td.attrib.get("data-th")
        value = (td.css("::text").get() or "").strip()
        if label and value:
            specifications[label] = value

    compliance = [text.strip() for text in sel.css(".compliant-block span::text").getall() if text.strip()]

    category = ga4_item.get("item_category3") or ga4_item.get("item_category2") or ga4_item.get("item_category")
    brand = product_ld.get("brand") or specifications.get("Brand") or None

    return RSProduct(
        name=product_ld.get("name") or "",
        url=response.context.get("url", ""),
        rs_stock_number=rs_stock_number or product_ld.get("sku", ""),
        mpn=mpn or None,
        brand=brand,
        description=product_ld.get("description") or None,
        price=str(offers.get("price")) if offers.get("price") is not None else None,
        currency=offers.get("priceCurrency") or None,
        availability=availability or None,
        stock_quantity=stock_quantity,
        min_order_qty=int(min_order_match.group(1)) if min_order_match else None,
        qty_increment=int(qty_increment_match.group(1)) if qty_increment_match else None,
        tiered_pricing=tiered_pricing,
        lead_time_required=(ga4_item.get("request_lead_time") == "Y") if ga4_item else None,
        datasheet_url=sel.css(".downloads-item a::attr(href)").get(),
        image=product_ld.get("image") or None,
        specifications=specifications,
        compliance=compliance,
        category=category,
    )


def parse_search(response: ScrapeApiResponse) -> Dict:
    sel = response.selector
    html = response.content

    results = []
    for row in sel.css("tr.product-item"):
        details = row.css(".product-item-details p::text").getall()
        mpn = rs_stock_number = None
        for detail in details:
            if "Manufacturer Part #:" in detail:
                mpn = detail.split("Manufacturer Part #:", 1)[1].strip()
            elif "RS Stock #:" in detail:
                rs_stock_number = detail.split("RS Stock #:", 1)[1].strip()

        price_text = " ".join(row.css(".product-price li:first-child ::text").getall())
        price_match = re.search(r"[\d,]+\.\d+", price_text)
        stock_number_text = row.css(".stock-badge__detail-number::text").get()

        results.append(RSSearchResult(
            name=row.css(".product-item-name a::text").get(),
            url=row.css(".product-item-name a::attr(href)").get(),
            rs_stock_number=rs_stock_number,
            mpn=mpn,
            price=price_match.group(0).replace(",", "") if price_match else None,
            currency=row.css(".product-price [data-currency-code]::attr(data-currency-code)").get(),
            availability=row.css(".stock-badge__label::text").get(),
            stock_quantity=int(stock_number_text.replace(",", "")) if stock_number_text else None,
            image=row.css(".product-item-photo img::attr(src)").get(),
        ))

    total_count = 0
    count_match = re.search(r"Showing\s+\d+\s+of\s+([\d,]+)\s+Results", html)
    if count_match:
        total_count = int(count_match.group(1).replace(",", ""))

    total_pages = 1
    page_totals = []
    for label in sel.css('[data-testid="pagination"] a::attr(aria-label)').getall():
        page_match = re.search(r" of (\d+)$", label)
        if page_match:
            page_totals.append(int(page_match.group(1)))
    if page_totals:
        total_pages = max(page_totals)

    return {"results": results, "total_pages": total_pages, "total_count": total_count}


async def scrape_products(urls: List[str]) -> List[RSProduct]:
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    products = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        if isinstance(response, ScrapflyScrapeError):
            log.error(f"failed to scrape product: {response.error}")
            continue
        try:
            log.info("scraping product {}", response.context["url"])
            products.append(parse_product(response))
        except Exception as e:
            log.error(f"failed to parse product: {e}")
    log.success(f"scraped {len(products)} products")
    return products


async def scrape_category(url: str, max_pages: int = 3) -> List[RSSearchResult]:
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG, render_js=True, wait_for_selector="[data-testid='pagination']"))
    data = parse_search(first_page)
    results = data["results"]
    total_pages = min(data["total_pages"], max_pages)

    if total_pages > 1:
        to_scrape = [
            ScrapeConfig(f"{url}?page={page}", **BASE_CONFIG, render_js=True, wait_for_selector="[data-testid='pagination']")
            for page in range(2, total_pages + 1)
        ]
        async for response in SCRAPFLY.concurrent_scrape(to_scrape):
            if isinstance(response, ScrapflyScrapeError):
                log.error(f"failed to scrape category page: {response.error}")
                continue
            try:
                results.extend(parse_search(response)["results"])
            except Exception as e:
                log.error(f"failed to parse category page: {e}")

    log.success(f"scraped {len(results)} category results")
    return results


async def scrape_search(query: str, max_pages: int = 3) -> List[RSSearchResult]:
    base_url = f"https://us.rs-online.com/catalogsearch/result/?q={query}"

    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(base_url, **BASE_CONFIG, render_js=True, wait_for_selector="[data-testid='pagination']"))
    data = parse_search(first_page)
    results = data["results"]
    total_pages = min(data["total_pages"], max_pages)

    if total_pages > 1:
        to_scrape = [
            ScrapeConfig(f"{base_url}&page={page}", **BASE_CONFIG, render_js=True, wait_for_selector="[data-testid='pagination']")
            for page in range(2, total_pages + 1)
        ]
        async for response in SCRAPFLY.concurrent_scrape(to_scrape):
            if isinstance(response, ScrapflyScrapeError):
                log.error(f"failed to scrape search page: {response.error}")
                continue
            try:
                results.extend(parse_search(response)["results"])
            except Exception as e:
                log.error(f"failed to parse search page: {e}")

    log.success(f"scraped {len(results)} search results")
    return results
