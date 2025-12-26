# https://gist.github.com/scrapfly-dev/cfdd232139838b7acbf681e02d6a9fbb
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

def parse_serps(response: ScrapeApiResponse) -> List[Dict]:
    """parse SERPs from bing search pages"""
    selector = response.selector
    data = []
    if "first" not in response.context["url"]:
        position = 0
    else:
        position = int(response.context["url"].split("first=")[-1])
    for result in selector.xpath("//li[@class='b_algo']"):
        url = result.xpath(".//h2/a/@href").get()
        description = result.xpath("normalize-space(.//div/p)").extract_first()
        date = result.xpath(".//span[@class='news_dt']/text()").get()
        if data is not None and date is not None and len(date) > 12:
            date_pattern = re.compile(r"\b\d{2}-\d{2}-\d{4}\b")
            date_pattern.findall(description)
            dates = date_pattern.findall(date)
            date = dates[0] if dates else None
        position += 1
        data.append(
            {
                "position": position,
                "title": "".join(result.xpath(".//h2/a//text()").extract()),
                "url": url,
                "origin": result.xpath(".//div[@class='tptt']/text()").get(),
                "domain": url.split("https://")[-1].split("/")[0].replace("www.", "")
                if url
                else None,
                "description": description,
                "date": date,
            }
        )
    return data


async def scrape_search(query: str, max_pages: int = None):
    """scrape bing search pages"""
    url = f"https://www.bing.com/search?{urlencode({'q': query})}"
    print("scraping the first search page")
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    serp_data = parse_serps(response)

    print(f"scraping search pagination ({max_pages - 1} more pages)")
    total_results = (max_pages - 1) * 10  # each page contains 10 results
    other_pages = [
        ScrapeConfig(url + f"&first={start}", **BASE_CONFIG)
        for start in range(10, total_results + 10, 10)
    ]

    # scrape the remaining search pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        data = parse_serps(response)
        serp_data.extend(data)
    print(f"scraped {len(serp_data)} search results from Bing search")
    return serp_data


async def main():
    serp_data = await scrape_search(query="web scraping emails", max_pages=3)
    with open("search_serps.json", "w", encoding="utf-8") as file:
        json.dump(serp_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())