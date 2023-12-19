"""
This is an example web scraper for redfin.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-redfin/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
from typing import List, Dict
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])


BASE_CONFIG = {
    # Redfin.com requires Anti Scraping Protection bypass feature:
    "asp": True,
    # Set the proxy location to US
    "country": "US",
}


def parse_search_api(response: ScrapeApiResponse) -> List[Dict]:
    """parse JSON data from the search API"""
    return json.loads(response.content.replace("{}&&", ""))["payload"]["homes"]


def parse_property_for_sale(response: ScrapeApiResponse) -> List[Dict]:
    selector = response.selector
    price = selector.xpath("//div[@data-rf-test-id='abp-price']/div/text()").get()
    estimated_monthly_price = "".join(selector.xpath("//span[@class='est-monthly-payment']/text()").getall())
    address = (
        "".join(selector.xpath("//div[contains(@class, 'street-address')]/text()").getall())
        + " " + "".join(selector.xpath("//div[contains(@class, 'cityStateZip')]/text()").getall())
    )
    description = selector.xpath("//div[@id='marketing-remarks-scroll']/p/span/text()").get()
    images = [
        image.attrib["src"]
        for image in selector.xpath("//img[contains(@class, 'widenPhoto')]")
    ]
    details = [
        "".join(text_content.getall())
        for text_content in selector.css("div .keyDetails-value::text")
    ]
    features_data = {}
    for feature_block in selector.css(".amenity-group ul div.title"):
        label = feature_block.css("::text").get()
        features = feature_block.xpath("following-sibling::li/span")
        features_data[label] = [
            "".join(feat.xpath(".//text()").getall()).strip() for feat in features
        ]
    return {
        "address": address,
        "description": description,
        "price": price,
        "estimatedMonthlyPrice": estimated_monthly_price,
        "propertyUrl": str(response.context["url"]),
        "attachments": images,
        "details": details,
        "features": features_data,
    }


def parse_property_for_rent(response: ScrapeApiResponse):
    """get the rental ID from the HTML to use it in the API"""
    selector = response.selector
    data = selector.xpath("//meta[@property='og:image']").attrib["content"]
    try:
        rental_id = data.split("rent/")[1].split("/")[0]
        # validate the rentalId
        assert len(rental_id) == 36
        return rental_id
    except:
        print("proeprty isn't for rent")
        return None


async def scrape_search(url: str) -> List[Dict]:
    """scrape search data from the searh API"""
    # send a request to the search API
    search_api_response = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, country="US")
    )
    search_data = parse_search_api(search_api_response)
    log.success(f"scraped ({len(search_data)}) search results from the search API")
    return search_data


async def scrape_property_for_sale(urls: List[str]) -> List[Dict]:
    """scrape properties for sale data from HTML"""
    # add the property pages to a scraping list
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    properties = []
    # scrape all property pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_property_for_sale(response)
        properties.append(data)
    log.success(f"scraped {len(properties)} property listings for sale")
    return properties


async def scrape_property_for_rent(urls: List[str]) -> list[Dict]:
    """scrape properties for rent from the API"""
    api_urls = []
    properties = []
    for url in urls:
        response_html = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
        rental_id = parse_property_for_rent(response_html)
        if rental_id:
            api_urls.append(
                f"https://www.redfin.com/stingray/api/v1/rentals/{rental_id}/floorPlans"
            )
    # add the property pages API URLs to a scraping list
    to_scrape = [ScrapeConfig(url, country="US") for url in api_urls]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        properties.append(json.loads(response.content))
    log.success(f"scraped {len(properties)} property listings for rent")
    return properties
