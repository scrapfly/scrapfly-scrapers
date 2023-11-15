"""
This is an example web scraper for idealista.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
import re
import math
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from typing import Dict, List
from typing_extensions import TypedDict
from collections import defaultdict
from urllib.parse import urljoin
from pathlib import Path
from loguru import logger as log

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass web scraping blocking
    "asp": True,
    # set the proxy country to Spain
    "country": "ES",
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


def parse_province(response: ScrapeApiResponse) -> List[str]:
    """parse province page for area search urls"""
    selector = response.selector
    urls = selector.css("#location_list li>a::attr(href)").getall()
    return [urljoin(str(response.context["url"]), url) for url in urls]


# type hints fo expected results so we can visualize our scraper easier:
class PropertyResult(TypedDict):
    url: str
    title: str
    location: str
    price: int
    currency: str
    description: str
    updated: str
    features: Dict[str, List[str]]
    images: Dict[str, List[str]]
    plans: List[str]


def parse_property(response: ScrapeApiResponse) -> PropertyResult:
    """parse Idealista.com property page"""
    # load response's HTML tree for parsing:
    selector = response.selector
    css = lambda x: selector.css(x).get("").strip()
    css_all = lambda x: selector.css(x).getall()

    data = {}
    # Meta data
    data["url"] = str(response.context["url"])

    # Basic information
    data["title"] = css("h1 .main-info__title-main::text")
    data["location"] = css(".main-info__title-minor::text")
    data["currency"] = css(".info-data-price::text")
    data["price"] = int(css(".info-data-price span::text").replace(",", ""))
    data["description"] = "\n".join(css_all("div.comment ::text")).strip()
    data["updated"] = (
        selector.xpath("//p[@class='stats-text']" "[contains(text(),'updated on')]/text()").get("").split(" on ")[-1]
    )

    # Features
    data["features"] = {}
    #  first we extract each feature block like "Basic Features" or "Amenities"
    for feature_block in selector.css(".details-property-h2"):
        # then for each block we extract all bullet points underneath them
        label = feature_block.xpath("text()").get()
        features = feature_block.xpath("following-sibling::div[1]//li")
        data["features"][label] = ["".join(feat.xpath(".//text()").getall()).strip() for feat in features]

    # Images
    # the images are tucked away in a javascript variable.
    # We can use regular expressions to find the variable and parse it as a dictionary:
    image_data = re.findall("fullScreenGalleryPics\s*:\s*(\[.+?\]),", response.scrape_result["content"])[0]
    # we also need to replace unquoted keys to quoted keys (i.e. title -> "title"):
    images = json.loads(re.sub(r"(\w+?):([^/])", r'"\1":\2', image_data))
    data["images"] = defaultdict(list)
    data["plans"] = []
    for image in images:
        url = urljoin(str(response.context["url"]), image["imageUrl"])
        if image["isPlan"]:
            data["plans"].append(url)
        else:
            data["images"][image["tag"]].append(url)
    return data


async def scrape_provinces(urls: List[str]) -> List[str]:
    """
    Scrape province pages like:
    https://www.idealista.com/en/venta-viviendas/balears-illes/con-chalets/municipios
    for search page urls like:
    https://www.idealista.com/en/venta-viviendas/marbella-malaga/con-chalets/
    """
    # add province pages to a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    search_urls = []
    # scrape the province pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        search_urls.extend(parse_province(response))
    log.success(f"scraped {len(search_urls)} search URLs")
    return search_urls


def parse_search(response: ScrapeApiResponse) -> List[str]:
    """Parse search result page for 30 listings"""
    selector = response.selector
    urls = selector.css("article.item .item-link::attr(href)").getall()
    return [urljoin(str(response.context["url"]), url) for url in urls]


async def scrape_properties(urls: List[str]) -> List[PropertyResult]:
    """Scrape Idealista.com properties"""
    properties = []
    # add all property pages to a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        # skip invalid property pages
        if response.upstream_status_code != 200:
            log.warning(f"can't scrape property: {response.context['url']}")
            continue
        properties.append(parse_property(response))
    log.success(f"scraped {len(properties)} property listings")
    return properties


async def scrape_search(url: str, scrape_all_pages: bool, max_scrape_pages: int) -> List[str]:
    """
    Scrape search urls like:
    https://www.idealista.com/en/venta-viviendas/marbella-malaga/con-chalets/
    for proprety urls
    :param url: Search URL
    :param scrape_all_pages: Whether to scrape all pages found in search result:
    :param max_scrape_pages: Number of max pages to scrape
    """
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    property_urls = parse_search(first_page)
    total_results = first_page.selector.css("h1#h1-container").re(": (.+) houses")[0]
    total_pages = math.ceil(int(total_results.replace(",", "")) / 30)
    if total_pages > 60:
        print(f"search contains more than max page limit ({total_pages}/60)")
        total_pages = 60
    # scrape all available pages in the search if scrape_all_pages = True or max_scrape_pages > total_pages
    if scrape_all_pages == False and max_scrape_pages < total_pages:
        total_pages = max_scrape_pages
    else:
        total_pages = total_pages
    log.info(f"scraping {total_pages} of search results concurrently")
    # add the search pages to a scraping list
    to_scrape = [
        ScrapeConfig(first_page.context["url"] + f"pagina-{page}.htm", **BASE_CONFIG)
        for page in range(2, total_pages + 1)
    ]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        property_urls.extend(parse_search(response))
    # then scrape all property pages found in the search pages
    log.info(f"scraping {len(property_urls)} of proeprty pages concurrently")
    properties = await scrape_properties(urls=property_urls)
    return properties
