# https://gist.github.com/scrapfly-dev/73969723c2fa37536297e75e7c883103
import os
import math
import json
import asyncio

from typing import Dict, List
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

BASE_CONFIG = {
    "asp": True,
    "country": "US",
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def parse_product_page(response: ScrapeApiResponse) -> Dict:
    """parse hidden product data from product pages"""
    selector = response.selector
    script = selector.xpath("//script[contains(text(),'offers')]/text()").get()
    if not script:
        print(f"Could not find product data script on {response.context['url']}")
        return {}
    data = json.loads(script)
    return data


async def scrape_product(urls: List[str]) -> List[Dict]:
    """scrape trustpilot company pages"""
    products = []
    # add the product page URLs to a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    # scrape all the product pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_product_page(response)
        products.append(data)
    print(f"scraped {len(products)} product listings from product pages")
    return products


async def main():
    product_data = await scrape_product(
        urls=[
            "https://www.etsy.com/listing/1552627931",
            "https://www.etsy.com/listing/529765307",
            "https://www.etsy.com/listing/949905096",
        ]
    )

    # save the results to a json file
    with open("product_data.json", "w", encoding="utf-8") as file:
        json.dump(product_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())