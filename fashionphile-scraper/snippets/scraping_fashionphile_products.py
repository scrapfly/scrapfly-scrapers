# https://gist.github.com/scrapfly-dev/7813858d18444bace241ee881e624c57
import os
import json
import asyncio

from typing import Dict, List
from scrapfly import ScrapeConfig, ScrapflyClient

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "render_js": True,
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def convert_to_json_urls(urls):
    converted = []
    for url in urls:
        # Replace '/p/' with '/products/' and add '.json' at the end
        new_url = url.replace("/p/", "/products/") + ".json"
        converted.append(new_url)
    return converted


async def scrape_products(urls: List[str]) -> List[Dict]:
    """
    Scrape product data from Fashionphile product pages using the product API.
    """
    urls = convert_to_json_urls(urls)
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    products = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        # Extract just the product data from the JSON content
        content = response.result['result']['content']
        product_data = json.loads(content)['product']
        products.append(product_data)
        print(f"scraped {len(products)} product listings from product pages")
    return products


async def main():
    products_data = await scrape_products(
        urls=[
            "https://www.fashionphile.com/p/bottega-veneta-nappa-twisted-padded-intrecciato-curve-slide-sandals-36-black-1048096",
            "https://www.fashionphile.com/p/louis-vuitton-ostrich-lizard-majestueux-tote-mm-navy-1247825",
            "https://www.fashionphile.com/p/louis-vuitton-monogram-multicolor-lodge-gm-black-1242632",
        ]
    )
    # save the results to a json file
    with open("products_data.json", "w", encoding="utf-8") as file:
        json.dump(products_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())