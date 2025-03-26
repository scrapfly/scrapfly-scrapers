"""
This is an example web scraper for BestBuy.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import gzip
import json
import jmespath
from typing import Dict, List, Union
from parsel import Selector
from urllib.parse import urlencode, quote_plus
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass bestbuy.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
}


def parse_sitemaps(response: ScrapeApiResponse) -> List[str]:
    """parse links for bestbuy sitemap"""
    # decode the .gz file
    bytes_data = response.scrape_result['content'].encode('latin1')
    xml = str(gzip.decompress(bytes_data), 'utf-8')
    selector = Selector(xml)
    data = []
    for url in selector.xpath("//url/loc/text()"):
        data.append(url.get())
    return data


async def scrape_sitemaps(url: str) -> List[str]:
    """scrape link data from bestbuy sitemap"""
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    promo_urls = parse_sitemaps(response)
    log.success(f"scraped {len(promo_urls)} urls from sitemaps")
    return promo_urls


def refine_product(data: Dict) -> Dict:
    """refine the JSON product data"""
    parsed_product = {}
    specifications = data["shop-specifications"]["specifications"]["categories"]
    pricing = data["pricing"]["app"]["data"]["skuPriceDomain"]
    ratings = jmespath.search(
        """{
        featureRatings: aggregateSecondaryRatings,
        positiveFeatures: distillation.positiveFeatures[].{name: name, score: representativeQuote.score, totalReviewCount: totalReviewCount},
        negativeFeatures: distillation.negativeFeatures[].{name: name, score: representativeQuote.score, totalReviewCount: totalReviewCount}
        }""",
        data["reviews"]["app"],
    )
    faqs = []
    for item in data["faqs"]["app"]["questions"]["results"]:
        result = jmespath.search(
            """{
            sku: sku,
            questionTitle: questionTitle,
            answersForQuestion: answersForQuestion[].answerText
            }""",
            item,
        )
        faqs.append(result)

    # define the final parsed product
    parsed_product["specifications"] = specifications
    parsed_product["pricing"] = pricing
    parsed_product["ratings"] = ratings
    parsed_product["faqs"] = faqs

    return parsed_product


def parse_product(response: ScrapeApiResponse) -> Dict:
    """parse product data from bestbuy product pages"""
    selector = response.selector
    data = {}
    data["shop-specifications"] = json.loads(selector.xpath("//script[contains(@id, 'shop-specifications')]/text()").get())
    data["faqs"] = json.loads(selector.xpath("//script[contains(@id, 'content-question')]/text()").get())
    data["pricing"] = json.loads(selector.xpath("//script[contains(@id, 'pricing-price')]/text()").get())
    data["reviews"] = json.loads(selector.xpath("//script[contains(@id, 'ratings-and-reviews')]/text()").get())
 
    parsed_product = refine_product(data)
    return parsed_product


async def scrape_products(urls: List[str]) -> List[Dict]:
    """scrapy product data from bestbuy product pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    data = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            product_data = parse_product(response)
            data.append(product_data)
        except:
            pass
            log.debug("expired product page")
    log.success(f"scraped {len(data)} products from product pages")
    return data


def parse_search(response: ScrapeApiResponse):
    """parse search data from search pages"""
    selector = response.selector
    data = []
    for item in selector.css("#main-results .sku-item-list>li.sku-item"):
        name = item.css(".sku-title a::text").get()
        link = item.css(".sku-title a::attr(href)").get()
        price = selector.css('[data-testid=customer-price]>span::text').re('\d+\.\d{2}')[0]
        original_price = (selector.css('[data-testid=regular-price]>span::text').re('\d+\.\d{2}') or [None]) [0]
        sku = item.xpath("@data-sku-id").get()
        model = item.css(".sku-model .sku-value::text").get()
        _rating_data = item.css(".ratings-reviews p::text")
        rating = (_rating_data.re(r"\d+\.*\d*") or [None])[0]
        rating_count = int((_rating_data.re('(\d+) reviews') or [0])[0])
        images = item.css(".product-image::attr(src)").getall()

        data.append({
            "name": name,
            "link": "https://www.bestbuy.com" + link,
            "images": images,
            "sku": sku,
            "model": model,
            "price": price,
            "original_price": original_price,
            "rating": rating,
            "rating_count": rating_count,
        })
    if len(data):
        _total_count = selector.css(".item-count::text").re('\d+')[0]
        total_pages = int(_total_count) // len(data)
    else:
        total_pages = 1

    return {"data": data, "total_pages": total_pages}


async def scrape_search(search_query: str, sort: Union["-bestsellingsort", "-Best-Discount"] = None, max_pages=None):
    """scrape search data from bestbuy search"""

    def form_search_url(page_number: int):
        """form the search url"""
        base_url = "https://www.bestbuy.com/site/searchpage.jsp?"
        # search parameters
        params = {"st": quote_plus(search_query)}
        if page_number > 1:
            params["cp"] = page_number
        if sort:
            params["sp"] = sort
        return base_url + urlencode(params)
    
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(form_search_url(1), **BASE_CONFIG))
    data = parse_search(first_page)
    search_data = data["data"]
    total_pages = data["total_pages"]

    # get the number of total search pages to scrape
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    log.info(f"scraping search pagination, {total_pages - 1} more pages")
    # add the remaining pages to a scraping list to scrape them concurrently
    to_scrape = [
        ScrapeConfig(form_search_url(page_number), **BASE_CONFIG)
        for page_number in range(2, total_pages + 1)
    ]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_search(response)["data"]
        search_data.extend(data)
    
    log.success(f"scraped {len(search_data)} products from search pages")
    return search_data


def parse_reviews(response: ScrapeApiResponse) -> List[Dict]:
    """parse review data from the review API responses"""
    data = json.loads(response.scrape_result['content'])
    total_count = data["totalPages"]
    review_data = data["topics"]
    return {"data": review_data, "total_count": total_count}


async def scrape_reviews(skuid: int, max_pages: int=None) -> List[Dict]:
    """scrape review data from the reviews API"""
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(
        f"https://www.bestbuy.com/ugc/v2/reviews?page=1&pageSize=20&sku={skuid}&sort=MOST_RECENT",
        **BASE_CONFIG
    ))
    data = parse_reviews(first_page)
    review_data = data["data"]
    total_count = data["total_count"]

    # get the number of total review pages to scrape
    if max_pages and max_pages < total_count:
        total_count = max_pages

    log.info(f"scraping reviews pagination, {total_count - 1} more pages")
    # add the remaining pages to a scraping list to scrape them concurrently
    to_scrape = [
        ScrapeConfig(
            f"https://www.bestbuy.com/ugc/v2/reviews?page={page_number}&pageSize=20&sku={skuid}&sort=MOST_RECENT",
            **BASE_CONFIG
        )
        for page_number in range(2, total_count + 1)
    ]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_reviews(response)["data"]
        review_data.extend(data)

    log.success(f"scraped {len(review_data)} reviews from the reviews API")
    return review_data
