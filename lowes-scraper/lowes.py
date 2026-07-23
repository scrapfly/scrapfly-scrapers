"""
This is an example web scraper for lowes.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
import re
from typing import Dict, List, Optional, TypedDict
from urllib.parse import quote_plus, urlencode

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient


SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "proxy_pool": "public_residential_pool",
}


class LowesProduct(TypedDict):
    product_id: str
    item_number: Optional[str]
    model_id: Optional[str]
    url: str
    name: Optional[str]
    brand: Optional[str]
    price: Optional[float]
    selling_price: Optional[float]
    currency: Optional[str]
    description: Optional[str]
    specifications: Dict[str, str]
    images: List[str]
    store_number: Optional[str]
    zip_code: Optional[str]


class LowesSearchResult(TypedDict):
    product_id: str
    item_number: Optional[str]
    model_id: Optional[str]
    url: Optional[str]
    name: Optional[str]
    brand: Optional[str]
    price: Optional[float]
    currency: Optional[str]
    image: Optional[str]


class LowesStoreLocation(TypedDict):
    store_number: str
    name: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    phone: Optional[str]
    distance: Optional[float]


def _store_search_url(search_term: str, max_results: int = 10) -> str:
    return "https://www.lowes.com/store/api/search?" + urlencode(
        {"maxResults": max_results, "searchTerm": search_term, "responseGroup": "large"}
    )

def _state(response: ScrapeApiResponse) -> Dict:
    """get page state from __PRELOADED_STATE__ or __NEXT_DATA__"""
    script = response.selector.xpath("//script[contains(text(),'__PRELOADED_STATE__')]/text()").get()
    if script:
        match = re.search(r"__PRELOADED_STATE__['\"]\s*\]\s*=\s*(\{.*\})", script, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    raw = response.selector.css("script#__NEXT_DATA__::text").get()
    if raw:
        return json.loads(raw).get("props", {}).get("pageProps", {}) or {}
    return {}


def parse_product(response: ScrapeApiResponse) -> LowesProduct:
    """parse product data from lowes product pages"""
    state = _state(response)
    product_id = state.get("productId")
    details = state.get("productDetails") or {}
    detail = details.get(product_id) or next(iter(details.values()), {})
    product = detail.get("product") or {}
    location = detail.get("location") or {}

    price_info = (detail.get("mfePrice") or {}).get("price") or {}
    additional = price_info.get("additionalData") or {}
    price = additional.get("retailPrice")
    selling_price = additional.get("sellingPrice")
    if price is None or selling_price is None:
        for entry in (location.get("price") or {}).get("pricingDataList") or []:
            price = price if price is not None else entry.get("retailPrice")
            selling_price = selling_price if selling_price is not None else entry.get("finalPrice")

    images = [
        f"https://mobileimages.lowes.com{u}" if u.startswith("/") else u
        for u in [e.get("value") for e in product.get("imageUrls") or []]
        if u
    ]

    store = location.get("storeNumber") or (state.get("storeDetails") or {}).get("id")
    return {
        "product_id": product_id or product.get("omniItemId"),
        "item_number": product.get("itemNumber"),
        "model_id": product.get("modelId"),
        "url": response.context["url"],
        "name": product.get("title"),
        "brand": product.get("brand"),
        "price": float(price) if price is not None else None,
        "selling_price": float(selling_price) if selling_price is not None else None,
        "currency": price_info.get("currency"),
        "description": product.get("romanceCopy") or product.get("description"),
        "specifications": {s["key"]: s["value"] for s in product.get("specs") or [] if s.get("key") and s.get("value")},
        "images": images,
        "store_number": str(store) if store else None,
        "zip_code": location.get("zipcode") or (state.get("storeDetails") or {}).get("zip"),
    }


async def scrape_products(urls: List[str]) -> List[LowesProduct]:
    """scrape product data from lowes product pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    products = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        if not isinstance(response, ScrapeApiResponse):
            continue
        try:
            log.info("scraping product {}", response.context["url"])
            products.append(parse_product(response))
        except Exception as e:
            log.error(f"failed to scrape product: {e}")
    log.success(f"scraped {len(products)} products")
    return products


def parse_search(response: ScrapeApiResponse) -> Dict:
    """parse search results from a lowes search page"""
    state = _state(response)
    results = []
    for item in state.get("itemList") or []:
        product = item.get("product") or {}
        if not product.get("omniItemId"):
            continue
        price_info = (item.get("location") or {}).get("price") or {}
        price = price_info.get("sellingPrice")
        if price is None:
            for entry in price_info.get("pricingDataList") or []:
                price = entry.get("finalPrice")
                break
        price = float(price) if price is not None else None
        url = product.get("pdURL")
        image = product.get("alternateImageUrl") or product.get("imageUrl")
        results.append(
            {
                "product_id": product["omniItemId"],
                "item_number": product.get("itemNumber"),
                "model_id": product.get("modelId"),
                "url": f"https://www.lowes.com{url}" if url and url.startswith("/") else url,
                "name": product.get("description"),
                "brand": product.get("brand"),
                "price": price,
                "currency": "$" if price is not None else None,
                "image": f"https://mobileimages.lowes.com{image}" if image and image.startswith("/") else image,
            }
        )
    return {
        "data": results,
        "total_pages": (state.get("pagination") or {}).get("pageCount") or 1,
        "page_size": state.get("pageSize") or 24,
    }


async def scrape_search(query: str, max_pages: int = 3) -> List[LowesSearchResult]:
    """scrape Lowe's search results"""
    base_url = f"https://www.lowes.com/search?searchTerm={quote_plus(query)}"
    print(base_url)

    log.info(f"scraping the first search page for '{query}'")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(base_url, **BASE_CONFIG))
    data = parse_search(first_page)
    results = data["data"]
    total_pages = min(data["total_pages"], max_pages)

    log.info(f"scraping search pagination, remaining ({total_pages - 1}) more pages")
    to_scrape = [
        ScrapeConfig(f"{base_url}&offset={data['page_size'] * (page - 1)}", **BASE_CONFIG)
        for page in range(2, total_pages + 1)
    ]
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        if not isinstance(result, ScrapeApiResponse):
            continue
        try:
            results.extend(parse_search(result)["data"])
        except Exception as e:
            log.error(f"failed to scrape search page: {e}")

    log.success(f"scraped {len(results)} search results")
    return results



def parse_store_locations(response: ScrapeApiResponse) -> List[LowesStoreLocation]:
    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        return []
    locations = []
    for entry in data.get("stores") or []:
        store = entry.get("store") or {}
        if not store.get("id"):
            continue
        try:
            distance = float(entry["distance"])
        except (KeyError, TypeError, ValueError):
            distance = None
        locations.append(
            LowesStoreLocation(
                store_number=store["id"],
                name=store.get("store_name") or store.get("storeName"),
                address=store.get("address"),
                city=store.get("city"),
                state=store.get("state"),
                zip_code=store.get("zip"),
                phone=store.get("phone"),
                distance=distance,
            )
        )
    return locations

async def scrape_store_locations(zip_code: str, max_results: int = 10) -> List[LowesStoreLocation]:
    """scrape Lowe's store locations nearest to a zip code"""
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            _store_search_url(zip_code, max_results),
            headers={
                "accept": "application/json, text/plain, */*",
                "priority": "u=1, i",
                "referer": "https://www.lowes.com/store/",
                "x-component-location": "store-locator",
            },
            **BASE_CONFIG,
        )
    )
    locations = parse_store_locations(response)
    log.success(f"scraped {len(locations)} store locations for zip {zip_code}")
    return locations
