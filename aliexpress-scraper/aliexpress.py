"""
This is an example web scraper for Aliexpress.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-aliexpress/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import math
import os
from typing import Dict, List, TypedDict
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import jmespath
from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Glassdoor.com requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
}


def add_or_replace_url_parameters(url: str, **params):
    """adds url parameters or replaces them with new values"""
    parsed_url = urlparse(url)
    query_params = dict(parse_qsl(parsed_url.query))
    query_params.update(params)
    updated_url = parsed_url._replace(query=urlencode(query_params))
    return urlunparse(updated_url)


def extract_search(result: ScrapeApiResponse) -> Dict:
    """extract json data from search page"""
    # find script with page data in it
    script_with_data = result.selector.xpath('//script[contains(.,"_init_data_=")]')
    # select page data from javascript variable in script tag using regex
    data = json.loads(script_with_data.re(r"_init_data_\s*=\s*{\s*data:\s*({.+}) }")[0])
    return data["data"]["root"]["fields"]


def parse_search(result: ScrapeApiResponse):
    """Parse search page response for product preview results"""
    data = extract_search(result)
    parsed = []
    for result in data["mods"]["itemList"]["content"]:
        item = jmespath.search("""{
            id: productId,
            type: productType,
            thumbnail: image.imgUrl,
            title: title.displayTitle,
            price: prices.salePrice.minPrice,
            currency: prices.salePrice.currencyCode,
            selling_points: sellingPoints[].tagContent.tagText,
            rating: evaluation.starRating,
            trade: trade.tradeDesc,
            store_url: store.storeUrl,
            store_name: store.storeName,
            store_id: store.storeId,
            store_ali_id: store.aliMemberId
        }""", result)
        item['url'] = f"https://www.aliexpress.com/item/{item['id']}.html"
        item['thumbnail'] = f"https:{item['thumbnail']}"
        parsed.append(item)
    return parsed


async def scrape_search(url, max_pages: int = 60):
    """Scrape all search results and return parsed search result data"""
    log.info("scraping search url {}", url)
    # scrape first search page and find total result count
    first_page_result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    _first_page_data = extract_search(first_page_result)
    page_size = _first_page_data["pageInfo"]["pageSize"]
    total_pages = int(math.ceil(_first_page_data["pageInfo"]["totalResults"] / page_size))
    if total_pages > max_pages:
        total_pages = max_pages

    # scrape remaining pages concurrently
    product_previews = parse_search(first_page_result)
    log.info("search {} found {} pages", url, total_pages)
    other_pages = [
        ScrapeConfig(add_or_replace_url_parameters(first_page_result.context["url"], page=page), **BASE_CONFIG)
        for page in range(2, total_pages + 1)
    ]
    async for result in SCRAPFLY.concurrent_scrape(other_pages):
        if not isinstance(result, ScrapflyScrapeError):
            product_previews.extend(parse_search(result))
        else:
            log.error(f"failed to scrape {result.api_response.config['url']}, got: {result.message}")
    log.info("search {} scraped {} results", url, len(product_previews))
    return product_previews


class Product(TypedDict):
    name: str
    sku: str
    available: bool
    full_price: float
    discounted_price: float
    currency: str


def parse_product(result: ScrapeApiResponse) -> Product:
    """parse product HTML page for product data"""
    script_with_data = result.selector.xpath('//script[contains(text(),"window.runParams")]')
    data = json.loads(script_with_data.re(r"data: ({.+?}),\n")[0])
    product = jmespath.search("""{
        name: titleModule.subject,
        total_orders: titleModule.formatTradeCount,
        feedback: titleModule.feedbackRating,
        description_url: descriptionModule.descriptionUrl,
        description_short: pageModule.description,
        keywords: pageModule.keywords,
        images: imageModule.imagePathList,
        stock: quantityModule.totalAvailQuantity,
        seller: storeModule.{
            id: storeNum,
            url: storeURL,
            name: storeName,
            country: countryCompleteName,
            positive_rating: positiveRate,
            positive_rating_count: positiveNum,
            started_on: openTime,
            is_top_rated: topRatedSeller
        },
        specification: specsModule.props[].{
            name: attrName,
            value: attrValue
        },
        variants: skuModule.skuPriceList[].{
            name: skuAttr,
            sku: skuId,
            available: skuVal.availQuantity,
            stock: skuVal.inventory,
            full_price: skuVal.skuAmount.value,
            discount_price: skuVal.skuActivityAmount.value,
            currency: skuVal.skuAmount.currency
        }
    }""", data)
    product['specification'] = dict([v.values() for v in product['specification']])
    return product


async def scrape_product(url: str) -> List[Product]:
    """scrape aliexpress products by id"""
    log.info("scraping product: {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    return parse_product(result)


def parse_review_page(result: ScrapeApiResponse):
    """parse single review page"""
    parsed = []
    for box in result.selector.css(".feedback-item"):
        # to get star score we have to rely on styling where's 1 star == 20% width, e.g. 4 stars is 80%
        stars = int(box.css(".star-view>span::attr(style)").re("width:(\d+)%")[0]) / 20
        # to get options we must iterate through every options container
        options = {}
        for option in box.css("div.user-order-info>span"):
            name = option.css("strong::text").get("").strip()
            value = "".join(option.xpath("text()").getall()).strip()
            options[name] = value
        # parse remaining fields
        parsed.append(
            {
                "text": box.xpath('.//dt[contains(@class,"buyer-eedback")]/span[1]/text()').get("").strip(),
                "post_time": box.xpath('.//dt[contains(@class,"buyer-feedback")]/span[2]/text()').get("").strip(),
                "stars": stars,
                "order_info": options,
                "user": box.css(".user-name>a::text").get(),
                "images": box.css(".pic-view-item img::attr(src)").getall(),
            }
        )
    return parsed


async def scrape_product_reviews(seller_id: str, product_id: str, max_pages: int = 60):
    """scrape all reviews of aliexpress product"""

    def scrape_config_for_page(page):
        data = f"ownerMemberId={seller_id}&memberType=seller&productId={product_id}&companyId=&evaStarFilterValue=all+Stars&evaSortValue=sortlarest%40feedback&page={page}&currentPage={page-1 if page > 1 else 1}&startValidDate=&i18n=true&withPictures=false&withAdditionalFeedback=false&onlyFromMyCountry=false&version=&isOpened=true&translate=+Y+&jumpToTop=true&v=2"
        return ScrapeConfig(
            "https://feedback.aliexpress.com/display/productEvaluation.htm",
            body=data,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    # scrape first page of reviews and find total count of review pages
    first_page_result = await SCRAPFLY.async_scrape(scrape_config_for_page(1))
    total_reviews = first_page_result.selector.css("div.customer-reviews").re(r"\((\d+)\)")[0]
    total_pages = int(math.ceil(int(total_reviews) / 10))
    if total_pages > max_pages:
        total_pages = max_pages

    # create scrape configs for other pages
    # then scrape remaining review pages concurrently
    log.info(f"scraping reviews of product {product_id}, found {total_reviews} total reviews")
    scrape_configs = [scrape_config_for_page(page) for page in range(2, total_pages + 1)]
    reviews = parse_review_page(first_page_result)
    async for result in SCRAPFLY.concurrent_scrape(scrape_configs):
        reviews.extend(parse_review_page(result))
    return reviews

