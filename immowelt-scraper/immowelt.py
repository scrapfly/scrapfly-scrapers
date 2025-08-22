"""
This is an example web scraper for immowelt.de.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import json
import math

import re
from typing import Dict, List
from pathlib import Path
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from lzstring import LZString

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass web scraping blocking
    "asp": True,
    # set the proxy country to switzerland
    "country": "DE",
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


def parse_property_pages(response: ScrapeApiResponse) -> Dict:
    """parse lsiting data from property page"""
    # get the property id from the page URL
    # proeprty_id = str(response.context["url"]).split("expose/")[-1]
    selector = response.selector
    # extract the data from the script tag
    data_script = selector.xpath("//script[contains(text(),'UFRN_LIFECYCLE_SERVERREQUEST')]/text()").get()
    # find data in JSON.parse("<data>") pattern:
    _hidden_datasets = re.findall(r'JSON.parse\("(.*)"\)', data_script)
    # unescape escaped json characters like `\\"` to `"`
    _property_datastring = _hidden_datasets[0].encode("utf-8").decode("unicode_escape")
    property_data = json.loads(_property_datastring)
    # remove web app related keys
    parsed = {
        key: value
        for key, value in property_data["app_cldp"]["data"]["classified"].items()
        if key
        in [
            "sections",
            "id",
            "brand",
            "tags",
            "contactSections",
        ]
    }
    return parsed


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
        except Exception as e:
            log.warning("expired property page: {}", e)
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


def parse_search_pages(response: ScrapeApiResponse) -> Dict:
    """Parse search data from script tags using LZ-String decompression."""
    selector = response.selector
    script_content = selector.xpath('//script[contains(text(),"classified-serp-init-data")]/text()').get()
    json_blob_string = script_content.split('JSON.parse("', 1)[1].rsplit('")', 1)[0]
    outer_data = json.loads(json_blob_string.encode().decode("unicode_escape"))
    compressed_data = outer_data["data"]["classified-serp-init-data"]
    lz = LZString()
    decompressed_string = lz.decompressFromBase64(compressed_data)
    data = json.loads(decompressed_string)
    classifieds_data = data["pageProps"]["classifiedsData"]
    search_data = list(classifieds_data.values())
    total_count = data["pageProps"]["totalCount"]
    max_pages = math.ceil(total_count / len(search_data)) if search_data else 1
    return {"search_data": search_data, "max_pages": max_pages}


async def scrape_search(url: str, max_scrape_pages: int = None) -> List[Dict]:
    """scrape search pages from XHR call responses"""
    log.info("scraping first search page")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_search_pages(first_page)
    search_data = data["search_data"]
    max_pages = data["max_pages"]

    # get the total number of pages to scrape
    if max_scrape_pages and max_scrape_pages < max_pages:
        max_pages = max_scrape_pages
    log.info(f"scraping search pagination, remaining ({max_pages - 1}) more pages")

    # scrape the remaining search pages concurrently
    to_scrape = [ScrapeConfig(url + f"&page={page}", **BASE_CONFIG) for page in range(2, max_pages + 1)]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        search_data.extend(parse_search_pages(response)["search_data"])
    log.success(f"scraped {len(search_data)} properties from search")
    return search_data
