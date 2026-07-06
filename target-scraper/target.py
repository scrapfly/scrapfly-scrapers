"""
This is an example web scraper for Target.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import re
import json
from typing import Dict, List, Optional, TypedDict
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass target.com Akamai Bot Manager blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
    "proxy_pool": "public_residential_pool",
}


class Price(TypedDict):
    current_retail: Optional[float]
    reg_retail: Optional[float]
    formatted_current_price: Optional[str]
    location_id: Optional[int]


class ProductVariant(TypedDict):
    tcin: str
    price: Optional[Price]
    free_shipping: bool
    in_stock: bool


class Product(TypedDict):
    tcin: str
    title: Optional[str]
    rating: Optional[float]
    review_count: Optional[int]
    variants: List[ProductVariant]


MODULE_FULFILLMENT = "ProductDetailWebDatasourceFulfillmentAndVariations"
MODULE_WITH_STORE = "ProductDetailWebDatasourceWithStore"
MODULE_REVIEWS = "ProductDetailReviewsAndQuestions"


def _extract_deferred_modules(response: ScrapeApiResponse) -> Dict[str, Dict]:
    """collect deferred_enrichment module payloads from captured XHR calls"""
    modules = {}
    xhr_calls = response.scrape_result.get("browser_data", {}).get("xhr_call") or []
    for xhr in xhr_calls:
        if "deferred_enrichment/modules" not in xhr.get("url", ""):
            continue
        body = (xhr.get("response") or {}).get("body")
        if not body:
            continue
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            continue
        for module in data.get("modules", []):
            if module_type := module.get("module_type"):
                modules[module_type] = module.get("module_data", {})
    return modules


def _is_in_stock(fulfillment: Optional[Dict]) -> bool:
    if not fulfillment or fulfillment.get("sold_out"):
        return False
    if (fulfillment.get("shipping_options") or {}).get("availability_status") == "IN_STOCK":
        return True
    for store in fulfillment.get("store_options") or []:
        statuses = (
            (store.get("order_pickup") or {}).get("availability_status"),
            (store.get("in_store_only") or {}).get("availability_status"),
        )
        if "IN_STOCK" in statuses:
            return True
    return False


def parse_product(response: ScrapeApiResponse) -> Product:
    """parse product data from deferred_enrichment XHR modules captured on the PDP"""
    modules = _extract_deferred_modules(response)
    for name in (MODULE_FULFILLMENT, MODULE_WITH_STORE):
        if name not in modules:
            raise ValueError(f"missing deferred_enrichment module: {name}")

    fulfillment = modules[MODULE_FULFILLMENT]["data"]["product"]
    store = modules[MODULE_WITH_STORE]["data"]["product"]
    fulfillment_by_tcin = {c["tcin"]: c for c in fulfillment.get("children", [])}
    store_by_tcin = {c["tcin"]: c for c in store.get("children", [])}

    variants: List[ProductVariant] = []
    for tcin in sorted(set(fulfillment_by_tcin) | set(store_by_tcin)):
        store_child = store_by_tcin.get(tcin, {})
        fulfillment_child = fulfillment_by_tcin.get(tcin, {})
        price_data = store_child.get("price") or {}
        variants.append({
            "tcin": tcin,
            "price": {
                "current_retail": price_data.get("current_retail"),
                "reg_retail": price_data.get("reg_retail"),
                "formatted_current_price": price_data.get("formatted_current_price"),
                "location_id": price_data.get("location_id"),
            } if price_data else None,
            "free_shipping": (store_child.get("free_shipping") or {}).get("enabled", False),
            "in_stock": _is_in_stock(fulfillment_child.get("fulfillment")),
        })

    ratings = modules.get(MODULE_REVIEWS, {}).get("ratings_and_reviews") or {}
    tcin = fulfillment.get("tcin") or store.get("tcin")
    if not tcin:
        match = re.search(r"/A-(\d+)", response.context["url"])
        tcin = match.group(1) if match else None

    return {
        "tcin": tcin,
        "title": response.selector.css('h1[data-test="product-title"]::text').get(),
        "rating": ratings.get("average"),
        "review_count": ratings.get("count"),
        "variants": variants,
    }


async def scrape_product(url: str) -> Product:
    """scrape a Target product page and return parsed product data"""
    response = await SCRAPFLY.async_scrape(ScrapeConfig(
        url,
        **BASE_CONFIG,
        render_js=True,
        wait_for_selector="xhr:deferred_enrichment/modules",
        rendering_wait=5000,
    ))
    return parse_product(response)


def parse_availability(response: ScrapeApiResponse) -> Dict:
    """parse fulfillment and availability data from a product_summary_with_fulfillment_v1 response"""
    pass


async def scrape_availability(
    tcins: List[str],
    store_id: str,
    zip_code: str,
) -> Dict:
    """scrape product availability and fulfillment data from product_summary_with_fulfillment_v1"""
    pass


def parse_store_locations(response: ScrapeApiResponse) -> List[Dict]:
    """parse store location entries from a sitemap response"""
    pass


async def scrape_store_locations(url: str) -> List[Dict]:
    """scrape store location URLs from the Target store sitemap (stable fallback for store-id discovery)"""
    pass


def parse_search(response: ScrapeApiResponse) -> Dict:
    """parse product listing data from a search API response"""
    pass


async def scrape_search(
    keyword: str,
    store_id: str,
    max_pages: Optional[int] = None,
) -> List[Dict]:
    """scrape product search results and paginate through all result pages"""
    pass
