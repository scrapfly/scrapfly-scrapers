"""
This is an example web scraper for etsy.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import math
import json
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from typing import Dict, List
from loguru import logger as log

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass Etsy.com web scraping blocking
    "asp": True,
    # set the poxy location to US
    "country": "US",
}


def strip_text(text):
    """remove extra spaces while handling None values"""
    if text != None:
        text = text.strip()
    return text


def parse_search(response: ScrapeApiResponse) -> Dict:
    """parse data from Etsy search pages"""
    selector = response.selector
    data = []
    # get the total number of pages
    total_listings = int(selector.xpath("//span[contains(text(),' results,')]/text()").get().split("results")[0].strip().replace(",", ""))
    total_pages = math.ceil(total_listings / 64)

    for product in selector.xpath("//div[@data-search-results-lg]/ol/li"):
        link = product.xpath(".//a[contains(@class, 'listing-link')]/@href").get()
        rate = strip_text(product.xpath(".//span[contains(@class, 'review_stars')]/div/text()").get())
        number_of_reviews = product.xpath(".//span[contains(@class, 'review_stars')]/div/p/text()").get()
        if number_of_reviews:
            number_of_reviews = number_of_reviews.replace("(", "").replace(")", "")
            number_of_reviews = int(number_of_reviews.replace("k", "").replace(".", "")) * 100 if "k" in number_of_reviews else number_of_reviews
        price = product.xpath(".//span[@class='currency-value']/text()").get()
        original_price = product.xpath(".//span[contains(text(),'Original Price')]/text()").get()
        discount = strip_text(product.xpath(".//span[contains(text(),'off')]/text()").get())

        data.append({
            "productLink": '/'.join(link.split('/')[:5]) if link else None,
            "productTitle": strip_text(product.xpath(".//h3[contains(@class, 'text-caption')]/text()").get()),
            "productImage": product.xpath("//img[@data-listing-card-listing-image]/@src").get(),
            "seller": product.xpath(".//p[contains(@class, 'seller-shop-name')]/span/text()").get(),
            "estimatedArrival": product.xpath(".//span[@class='wt-no-wrap']/text()").get(),
            "listingType": "Paid listing" if product.xpath(".//span[@data-ad-label='Ad by Etsy seller']") else "Free listing",
            "productRate": float(rate) if rate else None,
            "numberOfReviews": int(number_of_reviews) if number_of_reviews else None,
            "freeShipping": "Yes" if product.xpath(".//span[contains(text(),'Free shipping')]/text()").get() else "No",
            "productPrice": float(price) if price else None,
            "priceCurrency": product.xpath(".//span[@class='currency-symbol']/text()").get(),
            "originalPrice": float(original_price.split("$")[-1].strip()) if original_price else "No discount",
            "discount": discount if discount else "No discount",
        })
    return {
        "search_data": data,
        "total_pages": total_pages
    }


def parse_product_page(response: ScrapeApiResponse) -> Dict:
    """parse hidden product data from product pages"""
    selector = response.selector
    script = selector.xpath("//script[contains(text(),'offers')]/text()").get()
    data = json.loads(script)
    return data


def parse_shop_page(response: ScrapeApiResponse) -> Dict:
    """parse hidden shop data from shop pages"""
    selector = response.selector
    script = selector.xpath("//script[contains(text(),'itemListElement')]/text()").get()
    data = json.loads(script)
    return data


async def scrape_search(url: str, max_pages: int = None) -> List[Dict]:
    """scrape product listing data from Etsy search pages"""
    log.info("scraping the first search page")
    # etsy search pages are dynaminc, requiring render_js enabled
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, wait_for_selector="//div[@data-search-pagination]", render_js=True, **BASE_CONFIG))
    data = parse_search(first_page)
    search_data = data["search_data"]

    # get the number of total pages to scrape
    total_pages = data["total_pages"]
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    log.info(f"scraping search pagination ({total_pages - 1} more pages)")
        # add the remaining search pages in a scraping list
    other_pages = [
        ScrapeConfig(url + f"&page={page_number}", wait_for_selector="//div[@data-search-pagination]", render_js=True, **BASE_CONFIG)
        for page_number in range(2, total_pages + 1)
    ]
    # scrape the remaining search pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        data = parse_search(response)
        search_data.extend(data["search_data"])
    log.success(f"scraped {len(search_data)} product listings from search")
    return search_data


async def scrape_product(urls: List[str]) -> List[Dict]:
    """scrape trustpilot company pages"""
    products = []
    # add the product page URLs to a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    # scrape all the product pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_product_page(response)
        products.append(data)
    log.success(f"scraped {len(products)} product listings from product pages")
    return products

async def scrape_shop(urls: List[str]) -> List[Dict]:
    shops = []
    # add the shop page URLs to a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    # scrape all the shop pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_shop_page(response)
        shops.append(data)
    log.success(f"scraped {len(shops)} shops from shop pages")
    return shops    