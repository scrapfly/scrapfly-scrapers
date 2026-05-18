# https://gist.github.com/scrapfly-dev/2908cba68eb1ba4cae9145f80e0f604a
import json
import os
import re
import asyncio

from typing import Dict, List
from nested_lookup import nested_lookup
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "lang": ["en-US"]
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def parse_product(result: ScrapeApiResponse):
    """Parse Ebay's product listing page for core product data"""
    sel = result.selector
    css_join = lambda css: "".join(sel.css(css).getall()).strip()  # join all selected elements
    css = lambda css: sel.css(css).get("").strip()  # take first selected element and strip of leading/trailing spaces

    item = {}
    item["url"] = css('link[rel="canonical"]::attr(href)')
    item["id"] = item["url"].split("/itm/")[1].split("?")[0]  # we can take ID from the URL
    item["price_original"] = css(".x-price-primary>span::text")
    item["price_converted"] = css(".x-price-approx__price ::text")  # ebay automatically converts price for some regions

    item["name"] = css_join("h1 span::text")
    item["seller_name"] = sel.xpath("//div[contains(@class,'info__about-seller')]/a/span/text()").get()
    item["seller_url"] = sel.xpath("//div[contains(@class,'info__about-seller')]/a/@href").get().split("?")[0]
    item["photos"] = sel.css('.ux-image-filmstrip-carousel-item.image img::attr("src")').getall()  # carousel images
    item["photos"].extend(sel.css('.ux-image-carousel-item.image img::attr("src")').getall())  # main image
    # description is an iframe (independant page). We can keep it as an URL or scrape it later.
    item["description_url"] = css("iframe#desc_ifr::attr(src)")
    # feature details from the description table:
    feature_table = sel.css("div.ux-layout-section--features")
    features = {}
    for feature in feature_table.css("dl.ux-labels-values"):
        # iterate through each label of the table and select first sibling for value:
        label = "".join(feature.css(".ux-labels-values__labels-content > div > span::text").getall()).strip(":\n ")
        value = "".join(feature.css(".ux-labels-values__values-content > div > span *::text").getall()).strip(":\n ")
        features[label] = value
    item["features"] = features
    return item


async def scrape_product(url: str) -> Dict:
    """Scrape ebay.com product listing page for product data"""
    print(f"scraping product: {url}")
    page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    product = parse_product(page)
    return product


async def main():
    product_data = await scrape_product("https://www.ebay.com/itm/332562282948")

    # save the results to a json file
    with open("product_data.json", "w", encoding="utf-8") as f:
        json.dump(product_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())