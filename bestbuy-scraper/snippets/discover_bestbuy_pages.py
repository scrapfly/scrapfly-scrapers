# https://gist.github.com/scrapfly-dev/e5b7587213da9d9d03eca0ee13e6548c
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

def parse_sitemaps(response: ScrapeApiResponse) -> List[str]:
    """parse links for bestbuy sitemap"""
    # decode the .gz file
    bytes_data = response.scrape_result["content"].encode("latin1")
    xml = str(gzip.decompress(bytes_data), "utf-8")
    selector = Selector(xml)
    data = []
    for url in selector.xpath("//url/loc/text()"):
        data.append(url.get())
    return data


async def scrape_sitemaps(url: str) -> List[str]:
    """scrape link data from bestbuy sitemap"""
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    promo_urls = parse_sitemaps(response)
    print(f"scraped {len(promo_urls)} urls from sitemaps")
    return promo_urls


async def main():
    sitemap_data = await scrape_sitemaps(
        # sample scraper for one sitemap, other sitemaps can be found at:
        # https://www.bestbuy.com/robots.txt
        url="https://sitemaps.bestbuy.com/sitemaps_promos.0000.xml.gz"
    )
    with open("sitemap_promos_data.json", "w", encoding="utf-8") as file:
        json.dump(sitemap_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())