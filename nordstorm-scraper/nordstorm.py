"""
This is an example web scraper for nordstorm.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
import jmespath
from typing import Dict, List
from urllib.parse import urlencode, parse_qs, urlparse
from nested_lookup import nested_lookup
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass nordstorm.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
    "render_js": True,
    "proxy_pool": "public_residential_pool"
}


def parse_product(data: dict) -> dict:
    core_product = data["coreProducts"][0]
    npt_parts = [part for part in core_product.get("nptHierarchy", "").split(".") if part]
    reviews = data.get("reviews") or {}
    product = jmespath.search(
        """{
        id: id,
        title: copyProductTitle,
        description: copyDescription,
        features: copyFeatures
        }""",
        data,
    )
    product["type"] = npt_parts[-1].replace("_", " ").title() if npt_parts else None
    product["typeParent"] = npt_parts[-2].replace("_", " ").title() if len(npt_parts) > 1 else None
    product["reviewAverageRating"] = reviews.get("averageRating")
    product["numberOfReviews"] = reviews.get("numberOfReviews")
    product["brand"] = {
        "brandName": data.get("labelDisplayName"),
        "brandUrl": data.get("brandLink"),
        "labelId": data.get("labelId"),
    }
    product["gender"] = (core_product.get("gender") or {}).get("label")
    product["media"] = []
    product["variants"] = {}
    for choice in core_product.get("coreChoices", []):
        product["media"].append(
            {
                "colorCode": choice["coreChoiceId"],
                "colorName": choice.get("displayColorDescription"),
                "urls": [shot["imageUrl"] for shot in choice.get("orderedShots", [])],
            }
        )
        for variant_item in choice.get("items", []):
            sku = variant_item.get("sku") or {}
            sku_id = sku.get("skuId")
            if not sku_id:
                continue
            proposition = (sku.get("propositions") or [{}])[0]
            pricings = proposition.get("pricings") or [{}]
            product["variants"][sku_id] = {
                "id": sku_id,
                "sizeId": (variant_item.get("sizeDimension1") or {}).get("code"),
                "colorId": choice["coreChoiceId"],
                "totalQuantityAvailable": (proposition.get("availability") or {}).get("shipQuantity", 0),
                "price": (pricings[0].get("sellingRetail") or {}).get("price"),
            }
    return product


def update_url_parameter(url, **params):
    """update url query parameter of an url with new values"""
    current_params = parse_qs(urlparse(url).query)
    updated_query_params = urlencode({**current_params, **params}, doseq=True)
    return url[: url.find("?")] + "?" + updated_query_params


def find_hidden_data(result: ScrapeApiResponse) -> dict:
    """extract hidden web cache from page html"""
    # use XPath to find script tag with data
    data = result.selector.xpath("//script[contains(.,'__INITIAL_CONFIG__')]/text()").get()
    data = data.split("=", 1)[-1].strip().strip(";")
    data = json.loads(data)
    return data


async def scrape_products(urls: List[str]):
    """scrape nordstorm product pages for product data"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    products = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = find_hidden_data(response)
        entities = data["productDisplay"]["productDisplaysById"]["entities"]
        products.append(parse_product(list(entities.values())[0]))
    log.success(f"scraped {len(products)} product listings from product pages")
    return products


async def scrape_search(url: str, max_pages: int = 10) -> List[Dict]:
    """Scrape nordstom search pages for product listings"""
    log.info(f"scraping search page {url}")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    # parse first page for product search data and total amount of pages:
    data = find_hidden_data(first_page)
    _first_page_results = nested_lookup("productResults", data)[0]
    products = list(_first_page_results["productsById"].values())
    paging_info = _first_page_results["query"]
    total_pages = paging_info["pageCount"]

    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    # then scrape other pages concurrently:
    log.info(f"scraping search pagination, remaining ({total_pages - 1}) more pages")
    _other_pages = [
        ScrapeConfig(update_url_parameter(url, page=page), **BASE_CONFIG) for page in range(2, total_pages + 1)
    ]
    async for result in SCRAPFLY.concurrent_scrape(_other_pages):
        data = find_hidden_data(result)
        data = nested_lookup("productResults", data)[0]
        products.extend(list(data["productsById"].values()))
    log.success(f"scraped {len(products)} product listings from search pages")
    return products
