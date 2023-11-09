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
    "country": "de",
    "headers": {
        "accept": "application/json",
        "accept-language": "en-US,en;q=0.9"
    }
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


def parse_property_page(response: ScrapeApiResponse):
    """parse property listing data from property pages"""
    selector = response.selector
    property_link = selector.xpath("//link[@rel='canonical']").attrib["href"]
    title = selector.xpath("//h1[@id='expose-title']/text()").get().strip()
    description = selector.xpath("//meta[@name='description']").attrib["content"]
    address = selector.xpath("//div[@class='address-block']/div/span[2]/text()").get()
    floors_number = selector.xpath("//dd[@class='is24qa-etage grid-item three-fifths']/text()").get().strip()
    living_space = selector.xpath("//dd[@class='is24qa-wohnflaeche-ca grid-item three-fifths']/text()").get().strip()
    vacant_from = selector.xpath("//dd[@class='is24qa-bezugsfrei-ab grid-item three-fifths']/text()").get().strip()
    number_of_rooms = selector.xpath("//dd[@class='is24qa-zimmer grid-item three-fifths']/text()").get().strip()
    garage = selector.xpath("//dd[@class='is24qa-garage-stellplatz grid-item three-fifths']/text()").get().strip()
    additional_sepcs = []
    for spec in selector.xpath("//div[contains(@class, 'criteriagroup boolean-listing')]//span[contains(@class, 'palm-hide')]"):
        additional_sepcs.append(spec.xpath("./text()").get())
    price_without_heating = selector.xpath("//dd[@class='is24qa-kaltmiete grid-item three-fifths']/text()").get().strip()
    price_per_meter = selector.xpath("//dd[@class='is24qa-preism² grid-item three-fifths']/text()").get().strip()
    basic_rent = selector.xpath("//div[@class='is24qa-kaltmiete-main-label is24-label font-s']/span/text()").get().strip()
    additional_costs = selector.xpath("//dd[@class='is24qa-nebenkosten grid-item three-fifths']/text()").extract()[1].replace("\n", "").strip()
    heating_costs = selector.css("dd.is24qa-heizkosten.grid-item.three-fifths::text").extract()[1].replace("\n", "").strip()
    total_rent = selector.xpath("//dd[@class='is24qa-gesamtmiete grid-item three-fifths font-bold']/text()").get().strip()
    deposit = selector.xpath("//dd[@class='is24-ex-spacelink grid-item three-fifths']/div/text()").get().strip()
    garage_parking_rent = selector.xpath("//dd[@class='is24qa-miete-fuer-garagestellplatz grid-item three-fifths']/text()").get()
    if garage_parking_rent:
        garage_parking_rent = garage_parking_rent.strip()
    construction_year = selector.xpath("//dd[@class='is24qa-baujahr grid-item three-fifths']/text()").get().strip()
    energy_sources = selector.xpath("//dd[@class='is24qa-wesentliche-energietraeger grid-item three-fifths']/text()").get().strip()
    energy_certificate = selector.xpath("//dd[@class='is24qa-energieausweis grid-item three-fifths']/text()").get().strip()
    energy_certificate_type = selector.xpath("//dd[@class='is24qa-energieausweistyp grid-item three-fifths']/text()").get().strip()
    energy_certificate_date = selector.xpath("//dd[@class='is24qa-baujahr-laut-energieausweis grid-item three-fifths']/text()").get().strip()
    final_energy_requirement = selector.xpath("//dd[@class='is24qa-endenergiebedarf grid-item three-fifths']/text()").get().strip()
    property_images = []
    for image in selector.xpath("//div[@class='sp-slides']//div[contains(@class, 'sp-slide')]"):
        property_images.append(image.xpath("./img").attrib["data-src"].split("/ORIG")[0])
    video_available = bool(selector.xpath("//button[@class='button slideToVideo is24-gallery-video-trigger']/text()").get())
    internet_speed = selector.xpath("//div[@class='grid-item desk-seven-tenths lap-three-fourths palm-six-eighths']/span[3]/span[@classname]/text()").get()
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
            "numberOfRooms": int(number_of_rooms),
            "Garage/parking space": garage,
            "additionalSpecs": additional_sepcs,
            "internetAvailable": internet_available,
            "internetSpeed": internet_speed
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
            "constructionYear": int(construction_year),
            "energySources": energy_sources,
            "energyCertificate": energy_certificate,
            "energyCertificateType": energy_certificate_type,
            "energyCertificateDate": int(energy_certificate_date),        
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


def parse_search_api(response: ScrapeApiResponse):
    """parse JSON data from the search API"""
    data = json.loads(response.scrape_result['content'])
    max_search_pages = data["searchResponseModel"]["resultlist.resultlist"]["paging"]["numberOfPages"]
    search_data = data["searchResponseModel"]["resultlist.resultlist"]["resultlistEntries"][0]["resultlistEntry"]
    # remove similar property listings from each property data
    for json_object in search_data:
        if "similarObjects" in json_object.keys():
            json_object.pop("similarObjects")
    return {
        "max_search_pages": max_search_pages,
        "search_data": search_data
    }


async def scrape_search(url: str, scrape_all_pages: bool, max_scrape_pages: int = 10) -> List[Dict]:
    """scrape property listings from the search API, which follows the same search page URLs"""
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    result_data = parse_search_api(first_page)
    search_data = result_data["search_data"]
    max_search_pages = result_data["max_search_pages"]
    if scrape_all_pages == False and max_scrape_pages < max_search_pages:
        max_scrape_pages = max_scrape_pages
    # scrape all available pages in the search if scrape_all_pages = True or max_pages > total_search_pages
    else:
        max_scrape_pages = max_search_pages
    log.info("scraping search {} pagination ({} more pages)", url, max_scrape_pages - 1)
    # scrape the remaining search pages
    for page in range(2, max_scrape_pages + 1):
        response = await SCRAPFLY.async_scrape(ScrapeConfig(
            first_page.context["url"].split("?pagenumber")[0] + f"?pagenumber={page}", **BASE_CONFIG
            ))
        data = parse_search_api(response)["search_data"]
        search_data.extend(data)
    log.info("scraped {} proprties from {}", len(search_data), url)
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