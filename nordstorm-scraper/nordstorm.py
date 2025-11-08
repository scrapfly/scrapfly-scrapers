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
}


def parse_product(data: dict) -> dict:
    # parse product basic data like id, name, features etc.
    product = jmespath.search(
        """{
        id: id,
        title: productTitle,
        type: productTypeName,
        typeParent: productTypeParentName,
        ageGroups: ageGroups,
        reviewAverageRating: reviewAverageRating,
        numberOfReviews: numberOfReviews,
        brand: brand,
        description: sellingStatement,
        features: features,
        gender: gender,
        isAvailable: isAvailable
        }""",
        data,
    )
    # product variants have their own colors, prices and photos:
    prices_by_sku = data["price"]["bySkuId"] if data["price"] else None
    colors_by_id = data["filters"]["color"]["byId"]
    product["media"] = []
    for media_item in data["mediaExperiences"]["carouselsByColor"]:
        item = jmespath.search(
            """{
                colorCode: colorCode,
                colorName: colorName
            }""",
            media_item,
        )
        item["urls"] = [i["url"] for i in media_item["orderedShots"]]
        product["media"].append(item)
    # Each product has SKUs(Stock Keeping Units) which are the actual variants:
    product["variants"] = {}
    for sku, sku_data in data["skus"]["byId"].items():
        # get basic variant data
        parsed = jmespath.search(
            """{
                id: id,
                sizeId: sizeId,
                colorId: colorId,
                totalQuantityAvailable: totalQuantityAvailable
            }""",
            sku_data,
        )
        # get variant price from
        parsed["price"] = prices_by_sku[sku]["regular"]["price"] if prices_by_sku else None
        # get variant color data
        parsed["color"] = jmespath.search(
            """{
            id: id,
            value: value,
            sizes: isAvailableWith,
            mediaIds: styleMediaIds,
            swatch: swatchMedia.desktop
            }""",
            colors_by_id[parsed["colorId"]],
        )
        product["variants"][sku] = parsed
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
        # extract only product data from the dataset
        # find first key "stylesById" and take first value (which is the current product)
        product = nested_lookup("stylesById", data)
        product = list(product[0].values())[0]
        # parse the final data using jmespath
        products.append(parse_product(product))
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
