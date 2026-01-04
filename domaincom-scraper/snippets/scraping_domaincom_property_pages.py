# https://gist.github.com/scrapfly-dev/28a056e52e13d3d7c7f29d30c927346a
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
    print(f"scraped {len(properties)} property listings")
    return properties


async def main():
    properties_data = await scrape_properties(
        urls = [
            "https://www.domain.com.au/610-399-bourke-street-melbourne-vic-3000-2018835548",
            "https://www.domain.com.au/property-profile/308-9-degraves-street-melbourne-vic-3000",
            "https://www.domain.com.au/1518-474-flinders-street-melbourne-vic-3000-17773317"
        ]
    )

    # save the results to a json file
    with open("properties_data.json", "w", encoding="utf-8") as f:
        json.dump(properties_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())