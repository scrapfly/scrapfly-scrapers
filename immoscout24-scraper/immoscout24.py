"""
This is an example web scraper for immoscout24.ch.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import json
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from typing import Dict, List
from pathlib import Path
from loguru import logger as log

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass web scraping blocking
    "asp": True,
    # set the proxy country to switzerland
    "country": "CH",
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


def parse_next_data(response: ScrapeApiResponse) -> Dict:
    """parse listing data from script tags"""
    selector = response.selector
    # The '.' checks the entire string content of the tag, not just the immediate text node.
    script_content = selector.xpath("//script[contains(., 'window.__INITIAL_STATE__')]/text()").get()
    if not script_content:
        log.warning(f"Could not find __INITIAL_STATE__ on page: {response.context['url']}")
        return None
    try:
        start = script_content.find("{")
        end = script_content.rfind("}") + 1
        if start == -1 or end == 0:
            log.warning(f"Could not extract JSON object from script on: {response.context['url']}")
            return None
        json_str = script_content[start:end]
        # Replace JavaScript's 'undefined' with a valid JSON 'null'
        json_str = json_str.replace("undefined", "null")
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        log.error(f"Error parsing JSON from {response.context['url']}: {e}")
        return None


async def scrape_properties(urls: List[str]) -> List[Dict]:
    """scrape listing data from immoscout24 proeprty pages"""
    # add the property pages in a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    properties = []
    # scrape all property pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_next_data(response)
        # handle expired property pages
        try:
            properties.append(data["listing"]["listing"])
        except:
            log.info("expired property page")
            pass
    log.info(f"scraped {len(properties)} property listings")
    return properties


async def scrape_search(url: str, scrape_all_pages: bool, max_scrape_pages: int = 10) -> List[Dict]:
    """scrape listing data from immoscout24 search pages"""
    # scrape the first search page first
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    log.info("scraping search page {}", url)
    data = parse_next_data(first_page)["resultList"]["search"]["fullSearch"]["result"]
    search_data = data["listings"]
    # get the number of maximum search pages available
    max_search_pages = data["resultCount"]
    # scrape all available pages in the search if scrape_all_pages = True or max_pages > total_search_pages
    if scrape_all_pages == False and max_scrape_pages < max_search_pages:
        total_pages = max_scrape_pages
    else:
        total_pages = max_search_pages
    log.info("scraping search {} pagination ({} more pages)", url, total_pages - 1)
    # add the remaining search pages in a scraping list
    other_pages = [
        ScrapeConfig(first_page.context["url"] + f"?pn={page}", asp=True, country="CH")
        for page in range(2, total_pages + 1)
    ]
    # scrape the remaining search pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        data = parse_next_data(response)
        search_data.extend(data["resultList"]["search"]["fullSearch"]["result"]["listings"])
    log.info("scraped {} proprties from {}", len(search_data), url)
    return search_data
