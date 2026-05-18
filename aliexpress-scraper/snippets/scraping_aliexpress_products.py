# https://gist.github.com/scrapfly-dev/e4333226d9c5d6ec3c32fc81ac968887
import json
import math
import os
import re
import asyncio

from typing import Dict, List
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    # Us locale, apply localization settings from the browser and then copy the aep_usuc_f cookie from devtools
    "headers": {
        "cookie": "aep_usuc_f=site=glo&province=&city=&c_tp=USD&region=US&b_locale=en_US&ae_u_p_s=2"
    }
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def parse_product(result: ScrapeApiResponse) -> Dict:
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


async def scrape_product(url: str) -> List[Dict]:
    """scrape aliexpress products by id"""
    print(f"scraping product: {url}")
    result = await SCRAPFLY.async_scrape(ScrapeConfig(
        url, **BASE_CONFIG, render_js=True, auto_scroll=True,
        rendering_wait=5000, js_scenario=[
            {"wait_for_selector": {"selector": "//div[@id='nav-specification']//button", "timeout": 5000}},
            {"click": {"selector": "//div[@id='nav-specification']//button", "ignore_if_not_visible": True}}
        ], proxy_pool="public_residential_pool", session="some-randomg-session"
    ))
    data = parse_product(result)
    print(f"successfully scraped product: {url}")    
    return data


async def main():
    product_results = await scrape_product(
        url="https://www.aliexpress.com/item/2255800741121659.html"
    )

    # save the results to a json file
    with open("product.json", "w", encoding="utf-8") as f:
        json.dump(product_results, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())