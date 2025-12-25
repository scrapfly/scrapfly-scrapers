# https://gist.github.com/scrapfly-dev/72a6f8dbca45c2bffcf8865e1d947d39
import json
import math
import os
import re
import asyncio

from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

BASE_CONFIG = {
    "asp": True,
    "country": "US",
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def _add_or_replace_url_parameters(url: str, **params):
    """adds url parameters or replaces them with new values"""
    parsed_url = urlparse(url)
    query_params = dict(parse_qsl(parsed_url.query))
    query_params.update(params)
    updated_url = parsed_url._replace(query=urlencode(query_params))
    return urlunparse(updated_url)


def parse_search(result: ScrapeApiResponse) -> List[Dict]:
    """Parse search result page for product previews"""
    previews = []
    product_boxes = result.selector.css("div.s-result-item[data-component-type=s-search-result]")
    for box in product_boxes:
        url = urljoin(result.context["url"], box.css("div>a::attr(href)").get()).split("?")[0]
        if "/slredirect/" in url:  # skip ads etc.
            continue
        rating = box.xpath("//div[@data-cy='reviews-block']//a[contains(@aria-label, 'out of')]/@aria-label").re_first(r"(\d+\.*\d*) out")
        rating_count = box.xpath("//div[@data-cy='reviews-block']//a[contains(@aria-label, 'ratings')]/@aria-label").get()
        previews.append(
            {
                "url": url,
                "title": box.css("div>a>h2::attr(aria-label)").get(),
                # big price text is discounted price
                "price": box.css(".a-price[data-a-size=xl] .a-offscreen::text").get(),
                # small price text is "real" price
                "real_price": box.xpath("//div[@data-cy='secondary-offer-recipe']//span[contains(@class, 'a-color-base') and contains(text(), '$')]/text()").get(),
                "rating": float(rating) if rating else None,
                "rating_count": int(rating_count.replace(',','').replace(" ratings", "")) if rating_count else None,
            }
        )
    print(f"parsed {len(previews)} product previews from search page {result.context['url']}")
    return previews


async def scrape_search(url: str, max_pages: Optional[int] = None) -> List[Dict]:
    """Scrape amazon search pages product previews"""
    print(f"{url}: scraping first page")
    # first, scrape the first page and find total pages:
    first_result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    results = parse_search(first_result)
    _paging_meta = first_result.selector.xpath("//*[@cel_widget_id='UPPER-RESULT_INFO_BAR-0']//span/text()").get()
    _total_results = int(re.findall(r"(?:over\s+)?([\d,]+)\s+results", _paging_meta)[0].replace(',', ''))
    _results_per_page = int(re.findall(r"\d+-(\d+)", _paging_meta)[0])
    total_pages = math.ceil(_total_results / _results_per_page)
    if max_pages and total_pages > max_pages:
        total_pages = max_pages

    # now we can scrape remaining pages concurrently
    print(f"{url}: found total results: {_total_results}, scraping {total_pages} pages concurrently")
    other_pages = [
        ScrapeConfig(
            _add_or_replace_url_parameters(first_result.context["url"], page=page), 
            **BASE_CONFIG
        )
        for page in range(2, total_pages + 1)
    ]
    async for result in SCRAPFLY.concurrent_scrape(other_pages):
        results.extend(parse_search(result))

    print(f"{url}: found total of {len(results)} product previews from search pages")
    return results


async def main():
    search_data = await scrape_search(
        url = "https://www.amazon.com/s?k=kindle",
        max_pages = 2
    )

    # save the data into a json file
    with open("search_data.json", "w", encoding="utf-8") as f:
        json.dump(search_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())