"""
This is an example web scraper for Aliexpress.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-aliexpress/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import uuid
import json
import math
import os
import re
from typing import Dict, List, TypedDict
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import jmespath
from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Aliexpress.com requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "country": "US",
    # aliexpress returns differnt results based on localization settings
    # apply localization settings from the browser and then copy the aep_usuc_f cookie from devtools
    "headers": {
        "cookie": "aep_usuc_f=site=glo&province=&city=&c_tp=USD&region=EG&b_locale=en_US&ae_u_p_s=2"
    }
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
    info: Dict
    pricing: Dict
    specifications: List[Dict]
    shipping: Dict
    faqs: List[Dict]
    seller: Dict
    reviewData: Dict


def parse_product(result: ScrapeApiResponse) -> Product:
    """parse product HTML page for product data"""
    selector = result.selector
    reviews = selector.xpath("//a[contains(@class,'reviewer--reviews')]/text()").get()
    rate = selector.xpath("//div[contains(@class,'rating--wrap')]/div").getall()
    sold_count = selector.xpath("//a[contains(@class, 'reviewer--sliderItem')]//span[contains(text(), 'sold')]/text()").get()
    available_count = selector.xpath("//div[contains(@class,'quantity--info')]/div/span/text()").get()
    info = {
        "name": selector.xpath("//h1[@data-pl]/text()").get(),
        "productId": int(result.context["url"].split("item/")[-1].split(".")[0]),
        "link": result.context["url"],
        "media": selector.xpath("//div[contains(@class,'slider--img')]/img/@src").getall(),
        "rate": len(rate) if rate else None,
        "reviews": int(reviews.replace(" Reviews", "")) if reviews else None,
        "soldCount": int(sold_count.replace(" sold", "").replace(",", "").replace("+", "")) if sold_count else 0,
        "availableCount": int(available_count.replace(" available", "")) if available_count else None
    }
    price = selector.xpath("//span[contains(@class,'price-default--current')]/text()").get()
    original_price = selector.xpath("//span[contains(@class,'price-default--original')]//text()").get()
    discount = selector.xpath("//span[contains(@class,'price--discount')]/text()").get()
    discount = selector.xpath("//span[contains(@class,'price--discount')]/text()").get()
    pricing = {
        "priceCurrency": "USD $",        
        "price": float(price.split("$")[-1]) if price else None, # for US localization
        "originalPrice": float(original_price.split("$")[-1]) if original_price else "No discount",
        "discount": discount if discount else "No discount",
    }
    shipping_cost = selector.xpath("//strong[contains(text(),'Shipping')]/text()").get()
    delivery = selector.xpath("//strong[contains(text(),'Delivery')]/span/text()").get()
    if not delivery:
        # Fallback selector 
        delivery = selector.xpath("//div[contains(@class,'dynamic-shipping-contentLayout')]//span[@style]/text()").get()
    shipping = {
        "cost": float(shipping_cost.split("$")[-1]) if shipping_cost else None,
        "currency": "$",
        "delivery": delivery
    }
    specifications = []
    for i in selector.xpath("//div[contains(@class,'specification--prop')]"):
        specifications.append({
            "name": i.xpath(".//div[contains(@class,'specification--title')]/span/text()").get(),
            "value": i.xpath(".//div[contains(@class,'specification--desc')]/span/text()").get()
        })
    faqs = []
    for i in selector.xpath("//div[@class='ask-list']/ul/li"):
        faqs.append({
            "question": i.xpath(".//p[@class='ask-content']/span/text()").get(),
            "answer": i.xpath(".//ul[@class='answer-box']/li/p/text()").get()
        })
    seller_link = selector.xpath("//a[@data-pl='store-name']/@href").get()
    seller_followers = selector.xpath("//div[contains(@class,'store-info')]/strong[2]/text()").get()
    seller_followers = int(float(seller_followers.replace('K', '')) * 1000) if seller_followers and 'K' in seller_followers else int(seller_followers) if seller_followers else None
    seller = {
        "name": selector.xpath("//a[@data-pl='store-name']/text()").get(),
        "link": seller_link.split("?")[0].replace("//", "") if seller_link else None,
        "id": int(seller_link.split("store/")[-1].split("?")[0]) if seller_link else None,
        "info": {
            "positiveFeedback": selector.xpath("//div[contains(@class,'store-info')]/strong/text()").get(),
            "followers": seller_followers
        }
    }
    return {
        "info": info,
        "pricing": pricing,
        "specifications": specifications,
        "shipping": shipping,
        "faqs": faqs,
        "seller": seller,
    }


async def scrape_product(url: str) -> List[Product]:
    """scrape aliexpress products by id"""
    log.info("retrieving a session ID")
    log.info("scraping product: {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(
        url, **BASE_CONFIG, render_js=True, auto_scroll=True,
        rendering_wait=15000, retry=False, timeout=150000, js_scenario=[
            {"wait_for_selector": {"selector": "//div[@id='nav-specification']//button", "timeout": 5000}},
            {"click": {"selector": "//div[@id='nav-specification']//button", "ignore_if_not_visible": True}}
        ]
    ))
    data = parse_product(result)
    reviews = await scrape_product_reviews(data["info"]["productId"], max_scrape_pages=3)
    data["reviewData"] = reviews
    log.success("successfully scraped product: {}", url)    
    return data


def parse_review_page(result: ScrapeApiResponse):
    data = json.loads(result.content)["data"]
    return {
        "max_pages": data["totalPage"],
        "reviews": data["evaViewList"],
        "evaluation_stats": data["productEvaluationStatistic"]
    }


async def scrape_product_reviews(product_id: str, max_scrape_pages: int = None):
    """scrape all reviews of aliexpress product"""

    def scrape_config_for_page(page):
        url = f"https://feedback.aliexpress.com/pc/searchEvaluation.do?productId={product_id}&lang=en_US&country=US&page={page}&pageSize=10&filter=all&sort=complex_default"
        return ScrapeConfig(
            url
        )

    # scrape first page of reviews and find total count of review pages
    first_page_result = await SCRAPFLY.async_scrape(scrape_config_for_page(1))
    data = parse_review_page(first_page_result)
    max_pages = data["max_pages"]

    if max_scrape_pages and max_scrape_pages < max_pages:
        max_pages = max_scrape_pages

    # create scrape configs for other pages and scrape them concurrently
    log.info(f"scraping reviews pagination of product {product_id}, {max_pages - 1} pages remaining")
    to_scrape = [scrape_config_for_page(page) for page in range(2, max_pages + 1)]
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        data["reviews"].extend(parse_review_page(result)["reviews"])
    log.success(f"scraped {len(data['reviews'])} from review pages")
    data.pop("max_pages")
    return data

