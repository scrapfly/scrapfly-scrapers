import re
import os
import gzip
import json
import asyncio

from parsel import Selector
from typing import Dict, List
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "proxy_pool":"public_residential_pool",
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def parse_product(response: ScrapeApiResponse) -> Dict:
    """parse product data from bestbuy product pages"""
    selector = response.selector
    data = {}

    product_scripts = selector.xpath("//script[contains(text(),'productBySkuId')]/text()").getall()
    for script_text in product_scripts:
        json_data = extract_json(script_text)
        if not json_data:
            continue
            
        rehydrate_key = extract_rehydrate_key(json_data)
        if not rehydrate_key:
            continue
    
        if 'productBySkuId' in _extract_nested(json_data, ["rehydrate", rehydrate_key, "data"], default={}):
            product_data = _extract_nested(json_data, ["rehydrate", rehydrate_key, "data", "productBySkuId"])
            
            # Determine data type based on available fields
            if not data.get("product-info") and product_data:
                data["product-info"] = product_data
                
            if not data.get("product-features") and product_data and "features" in product_data:
                data["product-features"] = product_data.get("features")
                
            if not data.get("buying-options") and product_data and "buyingOptions" in product_data:
                data["buying-options"] = product_data.get("buyingOptions")
                
            if not data.get("product-faq") and product_data and "questions" in product_data:
                data["product-faq"] = product_data.get("questions")

    return data


async def scrape_products(urls: List[str], max_review_pages: int = 1) -> List[Dict]:
    """scrapy product data from bestbuy product pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG, render_js=True) for url in urls]
    data = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            product_data = parse_product(response)
            data.append(product_data)
        except:
            pass
            print("expired selectors or product page")
    print(f"scraped {len(data)} products from product pages")
    return data


async def main():
    product_data = await scrape_products(
        urls=[
            "https://www.bestbuy.com/site/apple-macbook-air-13-inch-apple-m4-chip-built-for-apple-intelligence-16gb-memory-256gb-ssd-midnight/6565862.p",
            "https://www.bestbuy.com/site/apple-geek-squad-certified-refurbished-macbook-pro-16-display-intel-core-i7-16gb-memory-amd-radeon-pro-5300m-512gb-ssd-space-gray/6489615.p",
            "https://www.bestbuy.com/site/apple-macbook-pro-14-inch-apple-m4-chip-built-for-apple-intelligence-16gb-memory-512gb-ssd-space-black/6602741.p",
            "https://www.bestbuy.com/product/apple-macbook-air-13-inch-laptop-apple-m2-chip-built-for-apple-intelligence-16gb-memory-256gb-ssd-midnight/JJGCQ8WQR5/sku/6602763"
        ]
    )
    with open("products.json", "w", encoding="utf-8") as file:
        json.dump(product_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())