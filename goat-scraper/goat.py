"""
This is an example web scraper for goat.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import re
import json
import math
from typing import Dict, List
from pathlib import Path
from loguru import logger as log
from urllib.parse import urlencode
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse, ScrapflyError


SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass goat.com web scraping blocking(cloudflare)
    "unblocker": True,
    # set the proxy country to US
    "country": "US",
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


def find_hidden_data(result: ScrapeApiResponse) -> dict:
    """extract hidden NEXT_DATA from page html"""
    data = result.selector.css("script#__NEXT_DATA__::text").get()
    data = json.loads(data)
    return data


# the product fields of the older product pages (`productTemplate` in __NEXT_DATA__), in their order
PRODUCT_FIELDS = """
brandName color designer details gender ageGroups id internalShot maximumOfferCents midsole minimumOfferCents name
nickname productCategory productType releaseDate releaseDateName season silhouette sizeBrand sizeRange sizeType sizeUnit
sku slug specialDisplayPriceCents specialType status upperMaterial taxonomyLevel1 taxonomyLevel2 availableSizesNew
availableSizesNewV2 availableSizesNewWithDefects availableSizesUsed sizeOptions lowestPriceCents newLowestPriceCents
usedLowestPriceCents productTaxonomy featuredIn localizedSpecialDisplayPriceCents category micropostsCount sellingCount
usedForSaleCount withDefectForSaleCount isWantable isOwnable isResellable isAliasResellable isOfferable
isAvailabilityRestricted directShipping isFashionProduct isRaffleProduct renderImagesInOrder applePayOnlyPromo
singleGender storyHtml story pictureUrl mainGlowPictureUrl mainPictureUrl gridGlowPictureUrl gridPictureUrl userWant
userOwn robotAssets productTemplateExternalPictures
""".split()


def find_streamed_data(result: ScrapeApiResponse) -> dict:
    """newer product pages (goat.com/product/...) have no __NEXT_DATA__: their data comes in self.__next_f chunks"""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', result.content)
    text = "".join(json.loads(chunk) for chunk in chunks)
    start = text.find('"initial":{"product":')
    if start == -1:
        raise ValueError(f"goat.com product page has no product data: {result.context['url']}")
    data, _ = json.JSONDecoder().raw_decode(text, start + len('"initial":'))
    return data


def parse_streamed_product(data: dict) -> dict:
    """map the newer page's product to the fields of the older pages (null when the page no longer has the value)"""
    product = data["product"]
    raw = product.get("rawData") or {}  # the same product with snake_case keys
    facts = {fact["key"]: fact["value"] for fact in data.get("facts") or []}
    result = {}
    for field in PRODUCT_FIELDS:
        snake = re.sub(r"[A-Z]|(?<=[a-z])[0-9]", lambda m: "_" + m.group(0).lower(), field)  # taxonomyLevel1
        result[field] = product.get(field, raw.get(snake))
    gender = product.get("gender")
    result["gender"] = [gender] if isinstance(gender, str) else gender
    result["singleGender"] = gender if isinstance(gender, str) else None
    result["mainPictureUrl"] = product.get("pictureUrl")
    result["id"] = int(product["id"])
    result["details"] = product.get("colorway") or facts.get("colorway")
    result["midsole"] = facts.get("midsole")
    result["sizeOptions"] = product.get("sizeOptionsList")
    result["sizeRange"] = [option["value"] for option in product.get("sizeOptionsList") or []]
    result["specialDisplayPriceCents"] = (product.get("localizedSpecialDisplayPriceCents") or {}).get("amountUsdCents")
    return result


async def scrape_products(urls: List[str]) -> dict:
    """scrape goat.com product pages for product data"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    products = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        if isinstance(response, ScrapflyError):  # a failed request comes back as the error object, not raised
            log.error(f"skipping a page that could not be scraped: {response}")
            continue
        if not response.selector.css("script#__NEXT_DATA__"):
            # goat.com is moving its product pages to /product/... pages without __NEXT_DATA__
            product = parse_streamed_product(find_streamed_data(response))
            product["offers"] = None
            products.append(product)
            continue
        data = find_hidden_data(response)
        product = data["props"]["pageProps"]["productTemplate"]
        if data["props"]["pageProps"]["offers"]:
            product["offers"] = data["props"]["pageProps"]["offers"]["offerData"]
        else:
            product["offers"] = None
        products.append(product)
    log.success(f"scraped {len(products)} product listings from product pages")
    return products


async def scrape_search(query: str, max_pages: int = 10) -> List[Dict]:
    """Scrape goat.com search pages for product listings using the new web-api."""

    def make_page_url(page: int = 1):
        params = {
            "queryString": query,
            "pageLimit": "12",
            "pageNumber": page,
            "sortType": "1",
        }
        return f"https://www.goat.com/web-api/consumer-search/get-product-search-results?{urlencode(params)}"

    url_first_page = make_page_url(page=1)
    log.info(f"Scraping product search with query '{query}'")
    result_first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url=url_first_page, **BASE_CONFIG))
    first_page_data = json.loads(result_first_page.content)["data"]
    results = first_page_data.get("productsList", [])
    total_results = first_page_data.get("totalResults", 0)
    results_per_page = 12
    total_pages = math.ceil(total_results / results_per_page)

    if max_pages and max_pages < total_pages:
        total_pages = max_pages
    if total_pages > 1:
        log.info(f"Scraping search pagination ({total_pages-1} more pages)")
        to_scrape = [ScrapeConfig(make_page_url(page=page), **BASE_CONFIG) for page in range(2, total_pages + 1)]
        async for result in SCRAPFLY.concurrent_scrape(to_scrape):
            if isinstance(result, ScrapflyError):  # a failed request comes back as the error object, not raised
                log.error(f"skipping a page that could not be scraped: {result}")
                continue
            data = json.loads(result.content).get("data", {})
            items = data.get("productsList", [])
            results.extend(items)
    log.success(f"Scraped {len(results)} product listings from search")
    return results
