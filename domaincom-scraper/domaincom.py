"""
This is an example web scraper for domain.com.au

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
import jmespath
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from typing import Dict, List
from pathlib import Path
from loguru import logger as log


SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])


BASE_CONFIG = {
    # bypass domain.com.au scraping blocking
    "asp": True,
    # set the proxy country to australia
    "country": "AU",
}


output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


def parse_hidden_data(response: ScrapeApiResponse):
    """parse json data from script tags"""
    selector = response.selector
    script = selector.xpath("//script[@id='__NEXT_DATA__']/text()").get()
    data = json.loads(script)
    return data["props"]["pageProps"]["componentProps"]


def parse_repoerty_data(response: ScrapeApiResponse):
    """parse json data from script tags"""
    selector = response.selector
    script = selector.xpath("//script[@id='__NEXT_DATA__']/text()").get()
    json_data = json.loads(script)
    # property pages data are found in different structures
    try:  # listed property
        data = json_data["props"]["pageProps"]["componentProps"]
        data = parse_component_props(data)
        return data
    except Exception:  # usually sold property has different data structure
        data = json_data["props"]["pageProps"]
        data = parse_page_props(data)
        return data


def parse_page_props(data: Dict) -> Dict:
    """refine property pages data"""
    if not data:
        return
    data = data["__APOLLO_STATE__"]
    key = next(k for k in data if k.startswith("Property:"))
    data = data[key]
    result = jmespath.search(
        """{
        propertyId: propertyId,
        unitNumber: address.unitNumber,
        streetNumber: address.streetNumber,
        suburb: address.suburb,
        postcode: address.postcode
    }""",
        data,
    )
    # parse the photo data
    image_key = next(k for k in data if k.startswith("media("))
    result["gallery"] = []
    for image in data[image_key]:
        result["gallery"].append(image["url"])
    return result


def parse_component_props(data: Dict) -> Dict:
    """refine property pages data"""
    if not data:
        return
    result = jmespath.search(
        """{
    listingId: listingId,
    listingUrl: listingUrl,
    unitNumber: unitNumber,
    streetNumber: streetNumber,
    street: street,
    suburb: suburb,
    postcode: postcode,
    createdOn: createdOn,
    propertyType: propertyType,
    beds: beds,
    phone: phone,
    agencyName: agencyName,
    propertyDeveloperName: propertyDeveloperName,
    agencyProfileUrl: agencyProfileUrl,
    propertyDeveloperUrl: propertyDeveloperUrl,
    description: description,
    loanfinder: loanfinder,
    schools: schoolCatchment.schools,
    suburbInsights: suburbInsights,
    gallery: gallery,
    listingSummary: listingSummary,
    agents: agents,
    features: features,
    structuredFeatures: structuredFeatures,
    faqs: faqs
    }""",
        data,
    )
    return result


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


async def scrape_properties(urls: List[str]) -> List[Dict]:
    """scrape listing data from property pages"""
    # add the property page URLs to a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    properties = []
    # scrape all the property page concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        # parse the data from script tag and refine it
        data = parse_repoerty_data(response)
        data['url'] = response.context['url']
        properties.append(data)
    log.success(f"scraped {len(properties)} property listings")
    return properties


async def scrape_search(url: str, max_scrape_pages: int = None):
    """scrape property listings from search pages"""
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    log.info("scraping search page {}", url)
    data = parse_hidden_data(first_page)
    search_data = parse_search_page(data)
    # get the number of maximum search pages
    max_search_pages = data["totalPages"]
    # scrape all available pages if not max_scrape_pages or max_scrape_pages >= max_search_pages
    if max_scrape_pages and max_scrape_pages < max_search_pages:
        max_scrape_pages = max_scrape_pages
    else:
        max_scrape_pages = max_search_pages
    log.info(
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
    log.success(f"scraped ({len(search_data)}) from {url}")
    return search_data
