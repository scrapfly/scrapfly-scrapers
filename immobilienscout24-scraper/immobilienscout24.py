"""
This is an example web scraper for immobilienscout24.de.

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
    # set the proxy country to Germany
    "country": "de"
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


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


def strip_text(text):
    """remove extra spaces while handling None values"""
    if text != None:
        text = text.strip()
    return text


def parse_property_page(response: ScrapeApiResponse):
    """parse property listing data from property pages"""
    selector = response.selector
    property_link = selector.xpath("//link[@rel='canonical']").attrib["href"]
    title = strip_text(selector.xpath("//h1[@id='expose-title']/text()").get())
    description = selector.xpath("//meta[@name='description']").attrib["content"]
    address = selector.xpath("//div[@class='address-block']/div/span[2]/text()").get()
    floors_number = strip_text(selector.xpath("//dd[contains(@class, 'etage')]/text()").get())
    living_space = strip_text(selector.xpath("//dd[contains(@class, 'wohnflaeche')]/text()").get())
    vacant_from = strip_text(selector.xpath("//dd[contains(@class, 'bezugsfrei')]/text()").get())
    number_of_rooms = strip_text(selector.xpath("//dd[contains(@class, 'zimmer')]/text()").get())
    garage = strip_text(selector.xpath("//dd[contains(@class, 'garage-stellplatz')]/text()").get())
    additional_sepcs = []
    for spec in selector.xpath("//div[contains(@class, 'criteriagroup boolean-listing')]//span[contains(@class, 'palm-hide')]"):
        additional_sepcs.append(spec.xpath("./text()").get())
    price_without_heating = strip_text(selector.xpath("//dd[contains(@class, 'kaltmiete')]/text()").get())
    price_per_meter = strip_text(selector.xpath("//dd[contains(@class, 'preism')]/text()").get())
    basic_rent = strip_text(selector.xpath("//div[contains(@class, 'kaltmiete')]/span/text()").get())
    additional_costs = strip_text(selector.xpath("//dd[contains(@class, 'nebenkosten')]/text()").extract()[1].replace("\n", ""))
    heating_costs = strip_text(selector.xpath("//dd[contains(@class, 'heizkosten')]/text()").extract()[1].replace("\n", ""))
    total_rent = strip_text(selector.xpath("//dd[contains(@class, 'gesamtmiete')]/text()").get())
    deposit = strip_text(selector.xpath("//dd[contains(@class, 'ex-spacelink')]/div/text()").get())
    garage_parking_rent = selector.xpath("//dd[contains(@class, 'garagestellplatz')]/text()").get()
    if garage_parking_rent:
        garage_parking_rent = strip_text(garage_parking_rent)
    construction_year = strip_text(selector.xpath("//dd[contains(@class, 'baujahr')]/text()").get())
    energy_sources = strip_text(selector.xpath("//dd[contains(@class, 'wesentliche-energietraeger')]/text()").get())
    energy_certificate = strip_text(selector.xpath("//dd[@class='is24qa-energieausweis grid-item three-fifths']/text()").get())
    energy_certificate_type = strip_text(selector.xpath("//dd[contains(@class, 'energieausweis')]/text()").get())
    energy_certificate_date = strip_text(selector.xpath("//dd[contains(@class, 'baujahr-laut-energieausweis')]/text()").get())
    final_energy_requirement = strip_text(selector.xpath("//dd[contains(@class, 'endenergiebedarf')]/text()").get())
    property_images = []
    for image in selector.xpath("//div[@class='sp-slides']//div[contains(@class, 'sp-slide')]"):
        try:
            if image.xpath("./img").attrib["data-src"]:
                property_images.append(image.xpath("./img").attrib["data-src"].split("/ORIG")[0])
        except:
            pass
    video_available = bool(selector.xpath("//button[contains(@class, 'gallery-video')]/text()").get())
    internet_speed = selector.xpath("//a[contains(@class, 'mediaavailcheck')]/text()").get()
    internet_available = bool(internet_speed)
    agency_name = selector.xpath("//span[@data-qa='companyName']/text()").get()
    agency_address = ""
    for text in selector.xpath("//ul[li[span[@data-qa='companyName']]]/li[position() >= 3 and position() <= 4]/text()").getall():
        agency_address = agency_address + text

    # return the data into a JSON object
    data = {
        "id": int(property_link.split("/")[-1]),
        "title": title,
        "description": description,
        "address": address,
        "propertyLlink": property_link,
        "propertySepcs": {
            "floorsNumber": floors_number,
            "livingSpace": living_space,
            "livingSpaceUnit": "Square Meter",
            "vacantFrom": vacant_from,
            "numberOfRooms": int(number_of_rooms) if number_of_rooms is not None else None,
            "Garage/parking space": garage,
            "additionalSpecs": additional_sepcs,
            "internetAvailable": internet_available,
        },
        "price": {
                "priceWithoutHeadting": price_without_heating,
                "priceperMeter": price_per_meter,
                "additionalCosts": additional_costs,
                "heatingCosts": heating_costs,
                "totalRent": total_rent,
                "basisRent": basic_rent,
                "deposit": deposit,
                "garage/parkingRent": garage_parking_rent,
                "priceCurrency": price_without_heating.split(" ")[1],    
        },
        "building": {
            "constructionYear": int(construction_year) if construction_year is not None else None,
            "energySources": energy_sources,
            "energyCertificate": energy_certificate,
            "energyCertificateType": energy_certificate_type,
            "energyCertificateDate": int(energy_certificate_date) if energy_certificate_date is not None else None, 
            "finalEnergyRrequirement": final_energy_requirement,
        },
        "attachments": {
            "propertyImages": property_images,
            "videoAvailable": video_available,
        },
        "agencyName": agency_name,
        "agencyAddress": agency_address,
    }
    return data


def parse_search(response: ScrapeApiResponse) -> List[Dict]:
    """parse script tags for json search results """
    selector = response.selector
    script = selector.xpath("//script[contains(text(),'searchResponseModel')]/text()").get()
    json_data = [i for i in list(find_json_objects(script)) if "searchResponseModel" in i][0]["searchResponseModel"]["resultlist.resultlist"]
    search_data = json_data["resultlistEntries"][0]["resultlistEntry"]
    max_pages = json_data["paging"]["numberOfPages"]
    return {"search_data": search_data, "max_pages": max_pages}




async def scrape_search(url: str, scrape_all_pages: bool, max_scrape_pages: int = 10) -> List[Dict]:
    """scrape immobilienscout24 search pages"""
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_search(first_page)
    search_data = data["search_data"]
    max_search_pages = data["max_pages"]

    if scrape_all_pages == False and max_scrape_pages < max_search_pages:
        max_scrape_pages = max_scrape_pages
    # scrape all available pages in the search if scrape_all_pages = True or max_pages > total_search_pages
    else:
        max_scrape_pages = max_search_pages
    print(f"scraping search {url} pagination ({max_scrape_pages - 1} more pages)")

    # scrape the remaining search pages concurrently
    to_scrape = [
        ScrapeConfig(url + f"?pagenumber={page}", **BASE_CONFIG)
        for page in range(2, max_scrape_pages + 1)
    ]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        search_data.extend(parse_search(response)["search_data"])

    print(f"scraped {len(search_data)} proprties from {url}")
    return search_data


async def scrape_properties(urls: List[str]) -> List[Dict]:
    """scrape listing data from immoscout24 proeprty pages"""
    # add the property pages in a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    properties = []
    # scrape all property pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_property_page(response)
        # handle expired property pages
        try:
            properties.append(data)
        except:
            log.info("expired property page")
            pass
    log.info(f"scraped {len(properties)} property listings")
    return properties