"""
This is an example web scraper for immowelt.de.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import json
import math

from typing import Dict, List
from pathlib import Path
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass web scraping blocking
    "asp": True,
    # set the proxy country to switzerland
    "country": "DE"
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


def parse_property_pages(response: ScrapeApiResponse) -> Dict:
    """parse lsiting data from property page"""
    # get the property id from the page URL
    # proeprty_id = str(response.context["url"]).split("expose/")[-1]
    selector = response.selector
    # extract the data from the script tag
    next_data = selector.xpath("//script[@id='__NEXT_DATA__']/text()").get()
    next_data = json.loads(next_data)["props"]["pageProps"]["classified"]
    # remove web app related keys
    {key: next_data.pop(key, None) for key in ['metadata', 'tracking', 'advertising', 'seo', 'defaultBackToSearch']}
    return next_data


async def scrape_properties(urls: List[str]) -> List[Dict]:
    """scrape listings data from property pages"""
    # add all property pages to a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    properties = []
    # scrape all property pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            data = parse_property_pages(response)
            properties.append(data)
        except:
            log.warning("expired property page")
    log.success(f"scraped {len(properties)} property listings")
    return properties


def find_json_objects(text: str, decoder=json.JSONDecoder()):
    """Find JSON objects in text, and generate decoded JSON data"""
    pos = 0
    while True:
        match = text.find("{", pos)
        if match == -1:
            break
        try:
            result, index = decoder.raw_decode(text[match:])
            yield result
            pos = match + index
        except ValueError:
            pos = match + 1


def parse_search_pages(response: ScrapeApiResponse) -> List[Dict]:
    """parse search data from script tags"""
    selector = response.selector
    script = selector.xpath('//script[contains(text(),"classified-serp-init-data")]/text()').get()
    script = script.replace('window["__UFRN_FETCHER__"]=JSON.parse("', '').replace('");', '')
    script = script.encode().decode('unicode_escape')
    data = json.loads(script)['classified-serp-init-data']['pageProps']
    search_data = []
    for k, v in data['classifiedsData'].items():
        search_data.append(v)
    max_pages = math.ceil(data['totalCount'] / 30)
    return {'search_data': search_data, 'max_pages': max_pages}


async def scrape_search(url: str, max_scrape_pages: int = None) -> List[Dict]:
    """scrape search pages from XHR call responses"""
    log.info("scraping first search page")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_search_pages(first_page)
    search_data = data['search_data']
    max_pages = data['max_pages']

    # get the total number of pages to scrape
    if max_scrape_pages and max_scrape_pages < max_pages:
        max_pages = max_scrape_pages
    log.info(f"scraping search pagination, remaining ({max_pages - 1}) more pages")

    # scrape the remaining search pages concurrently
    to_scrape = [
        ScrapeConfig(url + f'&page={page}', **BASE_CONFIG)
        for page in range(2, max_pages + 1)
    ]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        search_data.extend(parse_search_pages(response)['search_data'])
    log.success(f"scraped {len(search_data)} properties from search")
    return search_data
