"""
This is an example web scraper for Shopify stores.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import json
import os
from typing import Any, Dict, List, Optional, TypedDict
from urllib.parse import urlparse

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "US",
}


class ShopifyVariant(TypedDict):
    variant_id: Optional[str]
    title: Optional[str]
    sku: Optional[str]
    price: Optional[str]
    available: Optional[bool]


class ShopifyProduct(TypedDict):
    store_url: str
    source_url: str
    product_id: Optional[str]
    handle: Optional[str]
    title: Optional[str]
    vendor: Optional[str]
    product_type: Optional[str]
    variants: List[ShopifyVariant]
    images: List[str]


class SitemapEntry(TypedDict):
    url: str
    lastmod: Optional[str]
    changefreq: Optional[str]


def _normalize_store_url(store_url: str) -> str:
    store_url = store_url.strip()
    if "://" not in store_url:
        store_url = f"https://{store_url}"
    parsed = urlparse(store_url)
    return f"https://{parsed.netloc}"


def _parse_product(raw: Dict[str, Any], store_url: str) -> ShopifyProduct:
    """build a ShopifyProduct from a raw Shopify product dict"""
    handle = raw.get("handle")
    product_id = raw.get("id")

    return {
        "store_url": store_url,
        "source_url": f"{store_url}/products/{handle}" if handle else store_url,
        "product_id": str(product_id) if product_id is not None else None,
        "handle": handle,
        "title": raw.get("title"),
        "vendor": raw.get("vendor"),
        "product_type": raw.get("product_type"),
        "variants": [
            {
                "variant_id": str(v["id"]) if v.get("id") is not None else None,
                "title": v.get("title"),
                "sku": v.get("sku"),
                "price": v.get("price"),
                "available": v.get("available"),
            }
            for v in raw.get("variants") or []
            if isinstance(v, dict)
        ],
        "images": [img["src"] for img in raw.get("images") or [] if isinstance(img, dict) and img.get("src")],
    }


def _parse_catalog(response: ScrapeApiResponse, store_url: str) -> List[ShopifyProduct]:
    """parse a /products.json catalog page response"""
    data = json.loads(response.content)
    products = data.get("products") if isinstance(data, dict) else None
    if not products:
        log.warning("catalog response missing products key")
        return []

    return [_parse_product(product, store_url) for product in products if isinstance(product, dict)]


def _parse_product_json(response: ScrapeApiResponse, store_url: str) -> Optional[ShopifyProduct]:
    """parse a product from the /products/<handle>.json endpoint response"""
    data = json.loads(response.content)
    product = data.get("product") if isinstance(data, dict) else None
    return _parse_product(product, store_url) if isinstance(product, dict) else None


def _parse_product_html(response: ScrapeApiResponse, store_url: str) -> Optional[ShopifyProduct]:
    """parse a product from the raw HTML product page's JSON-LD data"""
    ld_json = response.selector.css('script[type="application/ld+json"]::text').get()
    if not ld_json:
        log.warning("no JSON-LD product data found in html")
        return None

    product = json.loads(ld_json)
    variant_nodes = product.get("hasVariant") or [product]
    if isinstance(variant_nodes, dict):
        variant_nodes = [variant_nodes]

    variants = []
    for v in variant_nodes:
        offers = v.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        availability = offers.get("availability")
        variants.append(
            {
                "variant_id": None,
                "title": v.get("name"),
                "sku": v.get("sku"),
                "price": offers.get("price"),
                "available": ("instock" in availability.lower()) if availability else None,
            }
        )

    brand = product.get("brand")
    url = response.context.get("url", store_url)
    images = product.get("image")
    if isinstance(images, str):
        images = [images]

    return {
        "store_url": store_url,
        "source_url": url,
        "product_id": product.get("productGroupID") or product.get("sku"),
        "handle": url.split("/products/")[-1].split("?")[0] if "/products/" in url else None,
        "title": product.get("name"),
        "vendor": brand.get("name") if isinstance(brand, dict) else brand,
        "product_type": product.get("category"),
        "variants": variants,
        "images": [i for i in (images or []) if isinstance(i, str)],
    }


def _parse_sitemap(response: ScrapeApiResponse) -> List[SitemapEntry]:
    """parse a Shopify XML sitemap response"""
    entries: List[SitemapEntry] = []
    for node in response.selector.xpath("//url | //sitemap"):
        loc = node.xpath("loc/text()").get()
        if not loc:
            continue
        entries.append(
            {
                "url": loc.strip(),
                "lastmod": node.xpath("lastmod/text()").get(),
                "changefreq": node.xpath("changefreq/text()").get(),
            }
        )
    return entries


async def scrape_sitemap(sitemap_url: str) -> List[SitemapEntry]:
    """scrape url data from a Shopify XML sitemap"""
    response = await SCRAPFLY.async_scrape(ScrapeConfig(sitemap_url, asp=False, render_js=False))
    return _parse_sitemap(response)


async def scrape_catalog(
    store_url: str,
    limit: Optional[int] = 250,
    max_pages: Optional[int] = 3,
) -> List[ShopifyProduct]:
    """scrape product catalog data from a Shopify store via /products.json"""
    store_url = _normalize_store_url(store_url)
    to_scrape = [
        ScrapeConfig(f"{store_url}/products.json?limit={limit}&page={page}", **BASE_CONFIG)
        for page in range(1, max_pages + 1)
    ]
    results: List[ShopifyProduct] = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        if isinstance(response, ScrapflyScrapeError):
            log.error(f"failed to scrape catalog page: {response.error}")
            continue
        try:
            results.extend(_parse_catalog(response, store_url))
        except Exception as e:
            log.error(f"failed to parse catalog page: {e}")
    return results


async def scrape_products(handles: List[str], store_url: str) -> List[ShopifyProduct]:
    """scrape individual product data via /products/<handle>.json, falling back to html"""
    store_url = _normalize_store_url(store_url)
    results: List[ShopifyProduct] = []
    json_enabled = True

    for handle in handles:
        product = None

        if json_enabled:
            try:
                response = await SCRAPFLY.async_scrape(
                    ScrapeConfig(f"{store_url}/products/{handle}.json", asp=False, render_js=False)
                )
                product = _parse_product_json(response, store_url)
            except Exception as e:
                log.warning(f"json request failed for {handle}: {e}, switching to html for remaining handles")
                json_enabled = False

        if not product:
            log.info(f"falling back to html for {handle}")
            response = await SCRAPFLY.async_scrape(
                ScrapeConfig(f"{store_url}/products/{handle}", **BASE_CONFIG)
            )
            product = _parse_product_html(response, store_url)

        if product:
            results.append(product)
        else:
            log.error(f"failed to scrape product {handle}")

    return results