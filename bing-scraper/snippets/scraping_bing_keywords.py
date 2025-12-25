# https://gist.github.com/scrapfly-dev/556f2423d2733b33e27a302a43cf9ae2
import re
import os
import json
import asyncio

from typing import Dict, List
from urllib.parse import urlencode
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

BASE_CONFIG = {
    "asp": True,
    "country": "GB",
    "proxy_pool": "public_residential_pool",
    "debug":True,
    "auto_scroll":True,
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def parse_keywords(response: ScrapeApiResponse) -> Dict:
    """parse FAQs and popular keywords on bing search pages"""
    selector = response.selector
    related_keywords = []
    for keyword in selector.xpath(".//li[@class='b_ans']/div/ul/li"):
        related_keywords.append("".join(keyword.xpath(".//a/div//text()").extract()))
    return related_keywords


async def scrape_keywords(query: str):
    """scrape bing search pages for keyword data"""
    url = f"https://www.bing.com/search?{urlencode({'q': query})}"
    print("scraping Bing search for keyword data")
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG, render_js=True))
    keyword_data = parse_keywords(response)
    print(f"scraped {len(keyword_data)} keywords from Bing search")
    return keyword_data


async def main():
    keyword_data = await scrape_keywords(query="web scraping emails")
    with open("search_keywords.json", "w", encoding="utf-8") as file:
        json.dump(keyword_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main()) 