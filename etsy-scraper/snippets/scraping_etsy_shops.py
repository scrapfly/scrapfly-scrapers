# https://gist.github.com/scrapfly-dev/b6f92473a40078f626c3208f0f2ea80d
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

def parse_shop_page(response: ScrapeApiResponse) -> Dict:
    """parse hidden shop data from shop pages"""
    selector = response.selector
    script = selector.xpath("//script[contains(text(),'itemListElement')]/text()").get()
    data = json.loads(script)
    return data


async def scrape_shop(urls: List[str]) -> List[Dict]:
    shops = []
    # add the shop page URLs to a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    # scrape all the shop pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_shop_page(response)
        data["url"] = response.context["url"]
        shops.append(data)
    print(f"scraped {len(shops)} shops from shop pages")
    return shops


async def main():
    shop_data = await scrape_shop(
        urls=[
            "https://www.etsy.com/shop/FalkelDesign",
            "https://www.etsy.com/shop/JoshuaHouseCrafts",
            "https://www.etsy.com/shop/Oakywood",
        ]
    )

    # save the results to a json file
    with open("shop_data.json", "w", encoding="utf-8") as file:
        json.dump(shop_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())