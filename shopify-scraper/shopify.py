"""
This is an example web scraper for Shopify storefronts.

Shopify stores share the same public storefront routes, though support for each route
is store dependent, so every scrape starts with a preflight that classifies the response.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import asyncio
import json
import os
from typing import Dict, List, Optional, Tuple, TypedDict
from urllib.parse import urljoin, urlparse

from loguru import logger as log
from parsel import Selector
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "US",
}

# the storefront JSON routes are classified by this scraper instead of failing on the status
# code, so upstream 403/404/429 responses have to reach the parser instead of raising
CLASSIFY_CONFIG = {**BASE_CONFIG, "raise_on_upstream_error": False}

CATALOG_PAGE_SIZE = 250  # highest page size the storefront products.json route accepts
CATALOG_PAGE_DELAY = 1.0  # seconds between catalog pages, Shopify rate limits bursts
CATALOG_MAX_RETRIES = 3


class ShopifyVariant(TypedDict):
    variant_id: str
    title: Optional[str]
    sku: Optional[str]
    options: List[str]
    price: Optional[float]
    compare_at_price: Optional[float]
    available: Optional[bool]


class ShopifyProduct(TypedDict):
    product_id: str
    handle: str
    url: str
    title: Optional[str]
    vendor: Optional[str]
    product_type: Optional[str]
    description: Optional[str]
    tags: List[str]
    options: Dict[str, List[str]]
    images: List[str]
    variants: List[ShopifyVariant]
    price_min: Optional[float]
    price_max: Optional[float]
    published_at: Optional[str]
    updated_at: Optional[str]


class ShopifyPreflight(TypedDict):
    store_url: str
    catalog_url: str
    status_code: int
    content_type: Optional[str]
    outcome: str
    product_count: Optional[int]
    is_shopify_catalog: bool


class ShopifyOffer(TypedDict):
    sku: Optional[str]
    title: Optional[str]
    price: Optional[float]
    currency: Optional[str]
    availability: Optional[str]
    url: Optional[str]


class ShopifyProductPage(TypedDict):
    url: str
    schema_type: Optional[str]
    product_id: Optional[str]
    name: Optional[str]
    brand: Optional[str]
    sku: Optional[str]
    description: Optional[str]
    images: List[str]
    price: Optional[float]
    currency: Optional[str]
    availability: Optional[str]
    offers: List[ShopifyOffer]
    variant_urls: List[str]


def _store_root(store_url: str) -> str:
    """normalize a store address to a scheme and host root without a trailing slash"""
    parsed = urlparse(store_url if "//" in store_url else f"https://{store_url}")
    if not parsed.netloc:
        raise ValueError(f"cannot resolve a store host from {store_url!r}")
    return f"{parsed.scheme or 'https'}://{parsed.netloc}"


def _catalog_url(store_url: str, page: int, limit: int, collection: Optional[str] = None) -> str:
    path = f"/collections/{collection}/products.json" if collection else "/products.json"
    return f"{_store_root(store_url)}{path}?limit={limit}&page={page}"


def _float(value) -> Optional[float]:
    """Shopify serializes storefront prices as strings, for example "91.00" """
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _text(html: Optional[str]) -> Optional[str]:
    """flatten a Shopify body_html field into plain text"""
    if not html:
        return None
    return " ".join(Selector(text=html).xpath("string()").get("").split()) or None


def classify_catalog_response(response: ScrapeApiResponse) -> Tuple[str, Optional[List[Dict]]]:
    """classify a storefront products.json response before any field is read

    Returns an outcome label and the product list when the response is a usable catalog:
    - shopify_catalog: JSON body with a non empty top level products array
    - empty_catalog:   JSON body with an empty products array, for example past the last page
    - rate_limited:    HTTP 429, the route exists but the request was throttled
    - unavailable:     any other non 2xx status, the route is missing, gated or blocked
    - not_json:        2xx body that does not parse as JSON, such as an HTML or login page
    - unexpected_json: 2xx JSON body without a products array, so not a Shopify catalog
    """
    if response.status_code == 429:
        return "rate_limited", None
    if response.status_code // 100 != 2:
        return "unavailable", None
    try:
        data = json.loads(response.content)
    except json.JSONDecodeError:
        return "not_json", None
    products = data.get("products") if isinstance(data, dict) else None
    if not isinstance(products, list):
        return "unexpected_json", None
    return ("shopify_catalog" if products else "empty_catalog"), products


def parse_preflight(response: ScrapeApiResponse, store_url: str) -> ShopifyPreflight:
    """turn a products.json preflight response into a capability report"""
    outcome, products = classify_catalog_response(response)
    return {
        "store_url": _store_root(store_url),
        "catalog_url": response.context["url"],
        "status_code": response.status_code,
        "content_type": response.scrape_result.get("response_headers", {}).get("content-type"),
        "outcome": outcome,
        "product_count": len(products) if products is not None else None,
        "is_shopify_catalog": outcome == "shopify_catalog",
    }


async def check_shopify_stores(store_urls: List[str]) -> List[ShopifyPreflight]:
    """preflight the products.json route of each store to see whether it serves catalog JSON

    A Shopify shaped response is strong evidence the route is usable right now. A failed
    response does not prove the store is not on Shopify, only that this route did not answer.
    """
    by_catalog_url = {_catalog_url(url, page=1, limit=1): url for url in store_urls}
    to_scrape = [ScrapeConfig(url, **CLASSIFY_CONFIG) for url in by_catalog_url]
    reports = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        if not isinstance(response, ScrapeApiResponse):
            continue
        try:
            report = parse_preflight(response, by_catalog_url[response.context["url"]])
            log.info("preflight {} -> {}", report["store_url"], report["outcome"])
            reports.append(report)
        except Exception as e:
            log.error(f"failed to preflight store: {e}")
    log.success(f"preflighted {len(reports)} stores")
    return reports


def parse_variant(variant: Dict) -> ShopifyVariant:
    """parse a single nested variant of a Shopify catalog product"""
    return {
        "variant_id": str(variant["id"]),
        "title": variant.get("title"),
        "sku": variant.get("sku") or None,
        "options": [variant[key] for key in ("option1", "option2", "option3") if variant.get(key)],
        "price": _float(variant.get("price")),
        "compare_at_price": _float(variant.get("compare_at_price")),
        "available": variant.get("available"),
    }


def parse_catalog_product(product: Dict, store_root: str) -> ShopifyProduct:
    """parse one product of a Shopify catalog response, keeping every variant intact"""
    variants = [parse_variant(v) for v in product.get("variants") or [] if v.get("id")]
    prices = [v["price"] for v in variants if v["price"] is not None]
    return {
        "product_id": str(product["id"]),
        "handle": product["handle"],
        "url": f"{store_root}/products/{product['handle']}",
        "title": product.get("title"),
        "vendor": product.get("vendor"),
        "product_type": product.get("product_type") or None,
        "description": _text(product.get("body_html")),
        "tags": product.get("tags") or [],
        "options": {o["name"]: o.get("values") or [] for o in product.get("options") or [] if o.get("name")},
        "images": [i["src"] for i in product.get("images") or [] if i.get("src")],
        "variants": variants,
        "price_min": min(prices) if prices else None,
        "price_max": max(prices) if prices else None,
        "published_at": product.get("published_at"),
        "updated_at": product.get("updated_at"),
    }


async def _scrape_catalog_page(url: str) -> Tuple[str, Optional[List[Dict]]]:
    """fetch one catalog page, retrying a bounded number of times on a rate limit"""
    for attempt in range(CATALOG_MAX_RETRIES + 1):
        response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **CLASSIFY_CONFIG))
        outcome, products = classify_catalog_response(response)
        if outcome != "rate_limited" or attempt == CATALOG_MAX_RETRIES:
            return outcome, products
        backoff = CATALOG_PAGE_DELAY * 2 ** (attempt + 1)
        log.warning(f"rate limited on {url}, retrying in {backoff}s")
        await asyncio.sleep(backoff)
    return "rate_limited", None


async def scrape_catalog(
    store_url: str,
    max_pages: int = 2,
    limit: int = CATALOG_PAGE_SIZE,
    collection: Optional[str] = None,
) -> List[ShopifyProduct]:
    """scrape products from a Shopify storefront products.json route

    Pagination is sequential and paced because the payload reports no page count, so the
    stop condition is a short, empty or failed page. Every run logs why it stopped, which
    keeps a partial run distinguishable from a complete one.
    """
    store_root = _store_root(store_url)
    products: List[ShopifyProduct] = []
    seen = set()
    stop_reason = f"reached max_pages={max_pages}"

    for page in range(1, max_pages + 1):
        url = _catalog_url(store_root, page=page, limit=limit, collection=collection)
        log.info(f"scraping catalog page {page} of {store_root}")
        outcome, page_products = await _scrape_catalog_page(url)
        if outcome != "shopify_catalog":
            stop_reason = f"page {page} returned {outcome}"
            break
        for product in page_products:
            if not product.get("id") or not product.get("handle") or product["id"] in seen:
                continue
            seen.add(product["id"])
            products.append(parse_catalog_product(product, store_root))
        if len(page_products) < limit:
            stop_reason = f"page {page} returned {len(page_products)} of {limit} products, last page"
            break
        await asyncio.sleep(CATALOG_PAGE_DELAY)

    log.success(f"scraped {len(products)} products from {store_root}, stopped: {stop_reason}")
    return products


async def scrape_collection(
    store_url: str, collection: str, max_pages: int = 2, limit: int = CATALOG_PAGE_SIZE
) -> List[ShopifyProduct]:
    """scrape products of a single Shopify collection, keeping the merchandising context

    Collection JSON support is store dependent: a store that serves /products.json can still
    return an empty list here, so treat an empty result as an unusable route, not an empty store.
    """
    return await scrape_catalog(store_url, max_pages=max_pages, limit=limit, collection=collection)


def _ld_nodes(response: ScrapeApiResponse) -> List[Dict]:
    """collect every JSON-LD node of a page, flattening arrays and @graph containers"""
    nodes = []
    for raw in response.selector.css('script[type="application/ld+json"]::text').getall():
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("skipping invalid JSON-LD block on {}", response.context["url"])
            continue
        for node in data if isinstance(data, list) else [data]:
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                nodes.extend(g for g in graph if isinstance(g, dict))
            else:
                nodes.append(node)
    return nodes


def _parse_offers(offers) -> List[ShopifyOffer]:
    """Shopify themes emit offers as a single object or as a list of variant offers"""
    entries = offers if isinstance(offers, list) else [offers] if isinstance(offers, dict) else []
    return [
        {
            "sku": offer.get("sku"),
            "title": offer.get("name"),
            "price": _float(offer.get("price") or (offer.get("priceSpecification") or {}).get("price")),
            "currency": offer.get("priceCurrency"),
            "availability": offer.get("availability"),
            "url": offer.get("url"),
        }
        for offer in entries
        if isinstance(offer, dict)
    ]


def parse_product_page(response: ScrapeApiResponse) -> ShopifyProductPage:
    """parse a Shopify product page through its JSON-LD block

    Themes use either Product or ProductGroup, so the schema type is validated before any
    field is mapped, and the type stays on the record.
    """
    node = next((n for n in _ld_nodes(response) if n.get("@type") in ("Product", "ProductGroup")), None)
    if node is None:
        raise ValueError(f"no Product or ProductGroup JSON-LD on {response.context['url']}")

    offers = _parse_offers(node.get("offers"))
    brand = node.get("brand")
    images = node.get("image") or []
    return {
        "url": response.context["url"],
        "schema_type": node.get("@type"),
        "product_id": node.get("productGroupID") or node.get("@id"),
        "name": node.get("name"),
        "brand": brand.get("name") if isinstance(brand, dict) else brand,
        "sku": node.get("sku"),
        "description": " ".join((node.get("description") or "").split()) or None,
        "images": [i for i in (images if isinstance(images, list) else [images]) if isinstance(i, str)],
        "price": offers[0]["price"] if offers else None,
        "currency": offers[0]["currency"] if offers else None,
        "availability": offers[0]["availability"] if offers else None,
        "offers": offers,
        "variant_urls": [v["url"] for v in node.get("hasVariant") or [] if isinstance(v, dict) and v.get("url")],
    }


async def scrape_product_pages(urls: List[str]) -> List[ShopifyProductPage]:
    """scrape Shopify product pages, the fallback when the catalog JSON route is unusable"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    products = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        if not isinstance(response, ScrapeApiResponse):
            continue
        try:
            log.info("scraping product page {}", response.context["url"])
            products.append(parse_product_page(response))
        except Exception as e:
            log.error(f"failed to scrape product page: {e}")
    log.success(f"scraped {len(products)} product pages")
    return products


def parse_sitemap_locations(response: ScrapeApiResponse) -> List[str]:
    """parse every loc entry of a sitemap index or a sitemap"""
    return response.selector.css("loc::text").getall()


async def scrape_product_urls(store_url: str, max_sitemaps: int = 1) -> List[str]:
    """discover product URLs from the Shopify sitemap index

    Shopify links its product sitemaps from /sitemap.xml with an id range query, so the index
    has to be read first: the numbered sitemap path on its own answers with a 400.
    """
    store_root = _store_root(store_url)
    index = await SCRAPFLY.async_scrape(ScrapeConfig(f"{store_root}/sitemap.xml", **BASE_CONFIG))
    product_sitemaps = [loc for loc in parse_sitemap_locations(index) if "sitemap_products" in loc][:max_sitemaps]
    log.info(f"found {len(product_sitemaps)} product sitemaps on {store_root}")

    urls = []
    to_scrape = [ScrapeConfig(loc, **BASE_CONFIG) for loc in product_sitemaps]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        if not isinstance(response, ScrapeApiResponse):
            continue
        try:
            urls.extend(urljoin(store_root, loc) for loc in parse_sitemap_locations(response) if "/products/" in loc)
        except Exception as e:
            log.error(f"failed to scrape product sitemap: {e}")

    log.success(f"scraped {len(urls)} product urls from {store_root}")
    return urls
