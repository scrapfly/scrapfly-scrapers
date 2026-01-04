# https://gist.github.com/scrapfly-dev/c81ee443c0c66fa06b243c26f7581ff0
import os
import json
import asyncio
import jmespath
from typing import Dict, List

from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

BASE_CONFIG = {
    "asp": True,
    "country": "AU",
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def parse_hidden_data(response: ScrapeApiResponse):
    """parse json data from script tags"""
    selector = response.selector
    script = selector.xpath("//script[@id='__NEXT_DATA__']/text()").get()
    data = json.loads(script)
    return data["props"]["pageProps"]["componentProps"]


def parse_search_page(data):
    """refine search pages data"""
    if not data:
        return
    data = data["listingsMap"]
    result = []
    # iterate over card items in the search data
    for key in data.keys():
        item = data[key]
        parsed_data = jmespath.search(
            """{
        id: id,
        listingType: listingType,
        listingModel: listingModel
      }""",
            item,
        )
        # execulde the skeletonImages key from the data
        parsed_data["listingModel"].pop("skeletonImages")
        result.append(parsed_data)
    return result


async def scrape_search(url: str, max_scrape_pages: int = None):
    """scrape property listings from search pages"""
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    print(f"scraping search page {url}")
    data = parse_hidden_data(first_page)
    search_data = parse_search_page(data)
    # get the number of maximum search pages
    max_search_pages = data["totalPages"]
    # scrape all available pages if not max_scrape_pages or max_scrape_pages >= max_search_pages
    if max_scrape_pages and max_scrape_pages < max_search_pages:
        max_scrape_pages = max_scrape_pages
    else:
        max_scrape_pages = max_search_pages
    print(
        f"scraping search pagination, remaining ({max_scrape_pages - 1} more pages)"
    )
    # add the remaining search pages to a scraping list
    other_pages = [
        ScrapeConfig(
            # paginate the search pages by adding a "?page" parameter at the end of the URL
            str(first_page.context["url"]) + f"?page={page}",
            **BASE_CONFIG,
        )
        for page in range(2, max_scrape_pages + 1)
    ]
    # scrape the remaining search pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        # parse the data from script tag
        data = parse_hidden_data(response)
        # append the data to the list after refining
        search_data.extend(parse_search_page(data))
    print(f"scraped ({len(search_data)}) from {url}")
    return search_data

async def main():
    search_data = await scrape_search(
        url="https://www.domain.com.au/sale/melbourne-vic-3000/", max_scrape_pages=1
    )

    # save the results to a json file
    with open("search_data.json", "w", encoding="utf-8") as f:
        json.dump(search_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())