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

from loguru import logger as log
from typing import Dict, List, TypedDict
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
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
        "cookie": "aep_usuc_f=site=glo&province=&city=&c_tp=USD&region=US&b_locale=en_US&ae_u_p_s=2"
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
    return data["mods"]["itemList"]["content"]


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

def _parse_count(text):
    """Parse count strings like '100K', '1M', '1,000+', 'similar items', etc."""
    if not text:
        return 0
    text = text.replace(" sold", "").replace(" available", "").replace(",", "").replace("+", "").strip()
    text = text.split()[0] if text else ""
    
    if not text:
        return 0
    multiplier = 1
    try:
        return int(float(text) * multiplier)
    except (ValueError, TypeError):
        return 0
    

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
        "soldCount": _parse_count(sold_count),
        "availableCount": _parse_count(available_count)
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
    delivery = selector.xpath("(//div[@class='dynamic-shipping']//strong/text())[2]").get()
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

    return {
        "info": info,
        "pricing": pricing,
        "specifications": specifications,
        "delivery": delivery,
        "faqs": faqs
    }


async def scrape_product(url: str) -> List[Product]:
    """scrape aliexpress products by id"""
    log.info("scraping product: {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(
        url, **BASE_CONFIG, render_js=True, proxy_pool="public_residential_pool", auto_scroll=True
    ))    
    data = parse_product(result)
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


def parse_category_page(response: ScrapeApiResponse):
    """Parse category page response for product preview results"""
    selector = response.selector
    script_data = selector.xpath('//script[contains(.,"_init_data_=")]')
    json_data = json.loads(script_data.re(r"_init_data_\s*=\s*{\s*data:\s*({.+}) }")[0])
    json_data = json_data['data']['root']['fields']
    product_data = json_data['mods']['itemList']['content']
    total_results = json_data['pageInfo']['totalResults']
    page_size = json_data['pageInfo']['pageSize']
    total_pages = int(math.ceil(total_results / page_size))
    return {
        'product_data': product_data,
        'total_pages': total_pages
    }


async def find_aliexpress_products(url: str, max_pages: int) -> List[Dict]:
    """Find Aliexpress products from category pages"""
    log.info(f"finding products from category page: {url}")
    first_page_result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    first_page_data = parse_category_page(first_page_result)
    all_product_data = first_page_data['product_data']
    total_pages = first_page_data['total_pages'] - 1 # exclude the first page from the count

    if max_pages is None:
        max_pages = total_pages
    log.info('found {} pages, but only scraping {} pages'.format(total_pages, max_pages))

    remaining_pages = [
        ScrapeConfig(url + f"?page={page}", **BASE_CONFIG)
        for page in range(2, max_pages + 1)
    ]

    async for result in SCRAPFLY.concurrent_scrape(remaining_pages):
        product_data = parse_category_page(result)['product_data']
        all_product_data.extend(product_data)
    
    log.success(f"discovered {len(all_product_data)} products from {url}")
    return all_product_data