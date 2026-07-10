"""
This is an example web scraper for DigiKey (digikey.com) electronic component data.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import json
from typing import Dict, List, Optional, TypedDict
from urllib.parse import quote
from loguru import logger as log
from lzstring import LZString
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
_LZSTRING = LZString()

BASE_CONFIG = {
    "asp": True,
    "render_js": True,
    "country": "us",
}


class DigikeyProduct(TypedDict):
    name: str
    url: str
    digikey_part_number: str
    manufacturer_part_number: Optional[str]
    manufacturer: Optional[str]
    description: Optional[str]
    category: Optional[str]
    price: Optional[str]
    currency: Optional[str]
    price_breaks: Optional[List[Dict[str, float]]]
    stock_quantity: Optional[int]
    availability: Optional[str]
    lead_time: Optional[str]
    min_order_qty: Optional[int]
    lifecycle_status: Optional[str]
    rohs_status: Optional[str]
    reach_status: Optional[str]
    msl_rating: Optional[str]
    datasheet_url: Optional[str]
    image: Optional[str]
    specifications: Dict[str, str]


class DigikeyCategoryResult(TypedDict):
    name: Optional[str]
    url: Optional[str]
    digikey_part_number: Optional[str]
    manufacturer_part_number: Optional[str]
    manufacturer: Optional[str]
    price: Optional[str]
    currency: Optional[str]
    stock_quantity: Optional[int]
    availability: Optional[str]
    image: Optional[str]


class DigikeyKeywordResult(TypedDict, total=False):
    name: str
    url: str
    manufacturer: str
    manufacturer_part_number: str
    price: str
    currency: str
    stock_quantity: int
    image: str


def _page_data(sel) -> tuple[Dict, Dict]:
    raw = sel.css("script#__NEXT_DATA__::text").get() or "{}"
    try:
        next_data = json.loads(raw)
    except json.JSONDecodeError:
        next_data = {}
    props = next_data.get("props", {})
    data = props.get("pageProps", {}).get("envelope", {}).get("data", {}) or {}
    return data, props


def _absolute_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return url
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith("/"):
        return f"https://www.digikey.com{url}"
    return url


def parse_product(response: ScrapeApiResponse) -> DigikeyProduct:
    sel = response.selector
    data, _ = _page_data(sel)

    product_ld = {}
    for script in sel.css('script[type="application/ld+json"]'):
        try:
            graph = json.loads(script.css("::text").get() or "{}").get("@graph", [])
        except json.JSONDecodeError:
            continue
        product_ld = next((node for node in graph if node.get("@type") == "Product"), {})
        if product_ld:
            break

    offers = product_ld.get("offers", {})

    overview = data.get("productOverview", {}) or {}
    price_quantity = data.get("priceQuantity", {}) or {}
    quantity_table = data.get("quantityTable") or []
    attrs_block = data.get("productAttributes", {}) or {}
    attributes = attrs_block.get("attributes") or []
    categories = attrs_block.get("categories") or []
    environmental = data.get("environmental", {}) or {}
    carousel_media = data.get("carouselMedia") or []
    messages = data.get("messages") or []

    specifications = {}
    lifecycle_status = None
    for attr in attributes:
        label = attr.get("label")
        values = attr.get("values") or []
        value = ", ".join(v.get("value", "") for v in values if v.get("value"))
        if label and value:
            specifications[label] = value
            if label == "Part Status":
                lifecycle_status = value

    env_map = {}
    for row in environmental.get("dataRows") or []:
        cells = row.get("dataCells") or []
        if len(cells) >= 2:
            label = cells[0].get("data", {}).get("value", {}).get("value")
            value = cells[1].get("data", {}).get("value", {}).get("value")
            if label and value:
                env_map[label] = value

    price_breaks = [
        {"quantity": tier["breakQty"], "unit_price": tier["unitPrice"]}
        for tier in quantity_table
        if tier.get("breakQty") is not None and tier.get("unitPrice") is not None
    ]

    image = next(
        (
            _absolute_url(media["displayUrl"])
            for media in carousel_media
            if media.get("type") == "Image" and media.get("displayUrl")
        ),
        None,
    )

    category = categories[-1].get("label") if categories else None

    if quantity_table:
        price = str(quantity_table[0]["unitPrice"])
    elif offers.get("price") is not None:
        price = str(offers["price"])
    else:
        price = None

    availability = next(
        (message.get("message", "").strip() for message in messages if message.get("type") == "title"),
        None,
    )
    if not availability and offers.get("availability"):
        availability = offers["availability"].replace("https://schema.org/", "")

    pricing_list = price_quantity.get("pricing") or []

    stock_quantity = None
    qty_available = price_quantity.get("qtyAvailable")
    if qty_available is not None:
        try:
            stock_quantity = int(str(qty_available).replace(",", ""))
        except ValueError:
            pass

    return DigikeyProduct(
        name=overview.get("title") or product_ld.get("name") or "",
        url=response.context.get("url", ""),
        digikey_part_number=overview.get("rolledUpProductNumber") or product_ld.get("sku") or "",
        manufacturer_part_number=overview.get("manufacturerProductNumber") or product_ld.get("mpn"),
        manufacturer=overview.get("manufacturer") or (product_ld.get("brand") or {}).get("name"),
        description=overview.get("detailedDescription") or overview.get("description") or product_ld.get("description"),
        category=category,
        price=price,
        currency=offers.get("priceCurrency") or "USD",
        price_breaks=price_breaks or None,
        stock_quantity=stock_quantity,
        availability=availability,
        lead_time=overview.get("standardLeadTime"),
        min_order_qty=pricing_list[0].get("minOrderQuantity") if pricing_list else None,
        lifecycle_status=lifecycle_status,
        rohs_status=env_map.get("RoHS Status"),
        reach_status=env_map.get("REACH Status"),
        msl_rating=env_map.get("Moisture Sensitivity Level (MSL)"),
        datasheet_url=_absolute_url(overview.get("datasheetUrl")),
        image=image,
        specifications=specifications,
    )


def parse_category(response: ScrapeApiResponse) -> List[DigikeyCategoryResult]:
    sel = response.selector
    data, props = _page_data(sel)
    currency = props.get("currency") or "USD"
    rows = data.get("products") or []

    results = []
    for row in rows:
        compare, detail, price_entries, qty_entries = {}, {}, [], []
        for cell in row:
            if not isinstance(cell, dict):
                continue
            value = cell.get("value")
            if isinstance(value, dict):
                if "detailUrl" in value:
                    detail = value
                elif "productNumber" in value:
                    compare = value
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                if "unitPrice" in value[0]:
                    price_entries = value
                elif "quantity" in value[0]:
                    qty_entries = value

        stock_quantity = None
        availability = None
        if qty_entries:
            try:
                stock_quantity = int(str(qty_entries[0].get("quantity")).replace(",", ""))
            except (ValueError, TypeError):
                stock_quantity = None
            availability = qty_entries[0].get("label")

        price = compare.get("price")
        if price is None and price_entries:
            raw_price = price_entries[0].get("unitPrice")
            try:
                price = str(float(raw_price.lstrip("$"))) if raw_price else None
            except (ValueError, AttributeError):
                price = raw_price

        image_obj = detail.get("image") or {}
        manufacturer_obj = compare.get("manufacturer")
        manufacturer = manufacturer_obj.get("Name") if isinstance(manufacturer_obj, dict) else manufacturer_obj

        results.append(DigikeyCategoryResult(
            name=detail.get("description"),
            url=_absolute_url(detail.get("detailUrl")),
            digikey_part_number=compare.get("productNumber"),
            manufacturer_part_number=compare.get("manufacturerPartNumber"),
            manufacturer=manufacturer,
            price=price,
            currency=currency,
            stock_quantity=stock_quantity,
            availability=availability,
            image=_absolute_url(image_obj.get("standard") or image_obj.get("thumb")),
        ))

    return results


async def scrape_products(urls: List[str]) -> List[DigikeyProduct]:
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    products = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        if isinstance(response, ScrapflyScrapeError):
            log.error("failed to scrape product: {}", response.error)
            continue
        try:
            log.info("scraping product {}", response.context["url"])
            products.append(parse_product(response))
        except Exception as e:
            log.error("failed to parse product: {}", e)
    log.success("scraped {} products", len(products))
    return products


async def scrape_category(url: str, max_pages: int = 3) -> List[DigikeyCategoryResult]:
    log.info("scraping category {}", url)
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    results = parse_category(first_page)

    if max_pages > 1:
        log.info("scraping category pagination ({} more pages)", max_pages - 1)
        to_scrape = []
        for page in range(2, max_pages + 1):
            payload = json.dumps({"5": {"p": page, "pp": 25}}, separators=(",", ":"))
            cursor = quote(_LZSTRING.compressToEncodedURIComponent(payload), safe="")
            sep = "&" if "?" in url else "?"
            to_scrape.append(ScrapeConfig(f"{url}{sep}s={cursor}", **BASE_CONFIG))
        async for response in SCRAPFLY.concurrent_scrape(to_scrape):
            if isinstance(response, ScrapflyScrapeError):
                log.error("failed to scrape category page: {}", response.error)
                continue
            try:
                results.extend(parse_category(response))
            except Exception as e:
                log.error("failed to parse category page: {}", e)

    log.success("scraped {} category results", len(results))
    return results


def parse_search(response: ScrapeApiResponse) -> List[DigikeyKeywordResult]:
    data, _ = _page_data(response.selector)
    results: List[DigikeyKeywordResult] = []

    for item in data.get("exactMatch") or []:
        raw_price = item.get("unitPrice")
        try:
            price = str(float(raw_price.lstrip("$"))) if raw_price else None
        except (ValueError, AttributeError):
            price = raw_price
        entry = DigikeyKeywordResult(
            name=item.get("description"),
            url=_absolute_url(item.get("detailUrl")),
            manufacturer_part_number=item.get("mfrProduct"),
            manufacturer=item.get("mfr"),
            price=price,
            currency="USD" if price else None,
            image=_absolute_url(item.get("imageUrl")),
        )
        results.append({k: v for k, v in entry.items() if v is not None})

    for item in data.get("topResults") or []:
        try:
            stock = int(str(item["productCount"]).replace(",", ""))
        except (ValueError, KeyError, TypeError):
            stock = None
        entry = DigikeyKeywordResult(
            name=item.get("categoryName"),
            url=_absolute_url(item.get("categoryUrl")),
            manufacturer=item.get("parentCategory"),
            stock_quantity=stock,
            image=_absolute_url(item.get("imageUrl")),
        )
        results.append({k: v for k, v in entry.items() if v is not None})

    pending = [(data.get("categories") or [], None)]
    while pending:
        nodes, parent = pending.pop(0)
        for node in nodes:
            if node.get("productCount") is not None:
                try:
                    stock = int(str(node["productCount"]).replace(",", ""))
                except (ValueError, TypeError):
                    stock = None
                entry = DigikeyKeywordResult(
                    name=node.get("label"),
                    url=_absolute_url(node.get("url")),
                    manufacturer=parent,
                    stock_quantity=stock,
                )
                results.append({k: v for k, v in entry.items() if v is not None})
            if node.get("subCategories"):
                pending.append((node["subCategories"], node.get("label") or parent))

    return results


async def scrape_search(keywords: str) -> List[DigikeyKeywordResult]:
    url = f"https://www.digikey.com/en/products/result?keywords={quote(keywords)}"
    log.info("scraping search results for keywords: {}", keywords)
    log.info("url: {}", url)
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    results = parse_search(response)
    log.success(f"scraped {len(results)} search results")
    return results
