# https://gist.github.com/scrapfly-dev/307450c738fbc28b228a54c1918121f2
import os
import re
import json
import math
import asyncio

from urllib.parse import urljoin
from typing import Dict, List, Literal
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

BASE_CONFIG = {
    "asp": True,
    "render_js" : True,
    "proxy_pool": "public_residential_pool"
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def parse_search_page(response: ScrapeApiResponse):
    """Parse company data from search pages with updated selectors."""
    data = []
    selector = response.selector

    # Extract total results count
    total_results_text = selector.xpath("//div[contains(text(), 'Products')]/following-sibling::div/text()").get()
    total_results = int(re.search(r"\((\d+)\)", total_results_text).group(1)) if total_results_text else 0

    _search_page_size = 20
    total_pages = math.ceil(total_results / _search_page_size) if total_results else 0

    # Main selector for each product card
    for result in selector.xpath("//section[.//a[contains(@href, '/products/')]]"):
        name = result.xpath(".//div[contains(@class, 'elv-text-lg')]/text()").get()

        relative_link = result.xpath(".//div[contains(@class, 'elv-text-lg')]/parent::a/@href").get()
        link = urljoin(response.request.url, relative_link)

        image = result.xpath(".//img[@alt='Product Avatar Image']/@src").get()

        raw_rate = result.xpath(".//label[contains(text(), '/5')]/text()").get()
        rate = float(raw_rate.split("/")[0]) if raw_rate else None

        raw_reviews = result.xpath(".//a[contains(@href, '#reviews')]//label[not(contains(text(), '/5'))]/text()").get()
        reviews_number = int(raw_reviews.strip("()")) if raw_reviews else None

        description_parts = result.xpath(".//div[div[contains(text(), 'Product Description')]]/p//text()").getall()
        description = "".join(description_parts).strip() if description_parts else None

        categories = result.xpath(".//aside//div[contains(@class, 'elv-whitespace-nowrap')]/text()").getall()

        if not name:
            continue

        data.append(
            {
                "name": name.strip() if name else None,
                "link": link,
                "image": image,
                "rate": rate,
                "reviewsNumber": reviews_number,
                "description": description if description else None,
                "categories": [cat.strip() for cat in categories],
            }
        )

    return {"search_data": data, "total_pages": total_pages}


async def scrape_search(url: str, max_scrape_pages: int = None) -> List[Dict]:
    """scrape company listings from search pages"""
    print(f"scraping search page {url}")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_search_page(first_page)
    search_data = data["search_data"]
    total_pages = data["total_pages"]

    # get the total number of pages to scrape
    if max_scrape_pages and max_scrape_pages < total_pages:
        total_pages = max_scrape_pages

    # scrape the remaining search pages concurrently and remove the successful request URLs
    print(f"scraping search pagination, remaining ({total_pages - 1}) more pages")
    remaining_urls = [url + f"&page={page_number}" for page_number in range(2, total_pages + 1)]
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in remaining_urls]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_search_page(response)
        search_data.extend(data["search_data"])
        # remove the successful requests from the URLs list
        remaining_urls.remove(response.context["url"])

    print(f"scraped {len(search_data)} company listings from search pages")
    return search_data


async def main():
    search_data = await scrape_search(
        url="https://www.g2.com/search?query=Infrastructure",
        max_scrape_pages=3
    )

    # save the results to a json file
    with open("search_data.json", "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())