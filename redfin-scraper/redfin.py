"""
This is an example web scraper for redfin.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-redfin/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
import re
from html import unescape
from typing import List, Dict
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])


BASE_CONFIG = {
    # Redfin.com requires Anti Scraping Protection bypass feature:
    "unblocker": True,
    # Set the proxy location to US
    "country": "US",
}


def parse_search_api(response: ScrapeApiResponse) -> List[Dict]:
    """parse JSON data from the search API"""
    return json.loads(response.content.replace("{}&&", ""))["payload"]["homes"]


def parse_data_cache(response: ScrapeApiResponse) -> Dict[str, Dict]:
    """parse the API answers embedded in a property page (root.__reactServerState), by API path"""
    html = response.content
    marker = "root.__reactServerState.InitialContext = "
    if marker not in html:
        title = response.selector.xpath("//title/text()").get("").strip()
        raise ValueError(f"redfin.com page has no property data: {title!r}")
    start = html.index(marker) + len(marker)
    state, _ = json.JSONDecoder().raw_decode(html, start)
    cache = {}
    for path, entry in state["ReactServerAgent.cache"]["dataCache"].items():
        text = (entry.get("res") or {}).get("text") or ""
        if text.startswith("{}&&"):  # the same JSON prefix as the search API
            cache[path] = json.loads(text[4:]).get("payload") or {}
    return cache


def feature_text(entry: Dict) -> str:
    """an amenity entry as "Name: value, value" (the values can hold HTML links)"""
    raw_values = entry.get("amenityValues") or []
    values = [unescape(re.sub(r"<[^>]+>", "", value)) for value in raw_values]
    text = ", ".join(values)
    return f"{entry['amenityName']}: {text}" if entry.get("amenityName") else text


def parse_property_for_sale(response: ScrapeApiResponse) -> Dict:
    """parse a property page from the API answers embedded in it"""
    cache = parse_data_cache(response)
    above_the_fold = cache.get("/stingray/api/home/details/aboveTheFold") or {}
    if "addressSectionInfo" not in above_the_fold:
        raise ValueError("redfin.com page has no property details (aboveTheFold)")
    address = above_the_fold["addressSectionInfo"]
    street = address["streetAddress"]["assembledAddress"]
    price = address.get("priceInfo") or {}  # list price, or last sold price of a sold home
    photos = (above_the_fold.get("mediaBrowserInfo") or {}).get("photos") or []
    house_info = cache.get("/stingray/api/home/details/mainHouseInfoPanelInfo") or {}
    remarks = (house_info.get("mainHouseInfo") or {}).get("marketingRemarks") or []
    below_the_fold = cache.get("/stingray/api/v1/home/details/belowTheFold") or {}
    amenities = below_the_fold.get("amenitiesInfo") or {}
    features_data = {}
    for super_group in amenities.get("superGroups") or []:
        for group in super_group.get("amenityGroups") or []:
            if not group.get("groupTitle"):  # the public facts block has no title
                continue
            entries = group.get("amenityEntries") or []
            features_data[group["groupTitle"]] = [feature_text(entry) for entry in entries]
    selector = response.selector
    details = []  # the key details block of the page, e.g. "Year Built: 1992"
    for row in selector.css(".keyDetails-value"):
        label = row.css(".valueType::text").get("")
        value = row.css(".valueText::text").get("")
        details.append(f"{label}: {value}")
    monthly = selector.css(".est-monthly-payment .monthly-payment ::text").getall()
    monthly_price = "".join(monthly).strip()
    return {
        "address": f"{street}, {address['city']}, {address['state']} {address['zip']}",
        "description": unescape(remarks[0]["marketingRemark"]) if remarks else None,
        "price": f"${price['amount']:,}" if price.get("amount") else None,
        "estimatedMonthlyPrice": f"Est. {monthly_price}" if monthly_price else "",
        "propertyUrl": str(response.context["url"]),
        "attachments": [photo["photoUrls"]["fullScreenPhotoUrl"] for photo in photos],
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
