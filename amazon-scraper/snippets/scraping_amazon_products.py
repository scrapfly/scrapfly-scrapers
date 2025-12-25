# https://gist.github.com/scrapfly-dev/2e9ef9628394626931ab223200431da2
import json
import os
import re
import asyncio

from typing import Dict, List
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

BASE_CONFIG = {
    "asp": True,
    "country": "US",
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def parse_product(result) -> Dict:
    """parse Amazon's product page (e.g. https://www.amazon.com/dp/B07KR2N2GF) for essential product data"""
    # images are stored in javascript state data found in the html
    # for this we can use a simple regex pattern that can be in one of those locations:
    images = []
    if color_images := re.findall(r"colorImages':.*'initial':\s*(\[.+?\])},\n", result.content):
        images = [img['large'] for img in json.loads(color_images[0])]
    if image_gallery := re.findall(r"imageGalleryData'\s*:\s*(\[.+\]),\n", result.content):
        images = [img['mainUrl'] for img in json.loads(image_gallery[0])]

    # the other fields can be extracted with simple css selectors
    # we can define our helper functions to keep our code clean
    sel = result.selector
    parsed = {
        "name": sel.css("#productTitle::text").get("").strip(),
        "asin": sel.css("input[name=ASIN]::attr(value)").get("").strip(),
        "style": ''.join(sel.xpath("//span[contains(@id, 'style_name_')]//text()").getall()).strip(),
        "description": '\n'.join(sel.css("#productDescription p span ::text").getall()).strip(),
        "stars": sel.css("i[data-hook=average-star-rating] ::text").get("").strip(),
        "rating_count": sel.css("span[data-hook=total-review-count] ::text").get("").strip(),
        "features": [value.strip() for value in sel.css("#feature-bullets li ::text").getall()],
        "images": images,
    }
    # extract details from "Product Information" table:
    info_table = {}
    for row in sel.css('#productDetails_detailBullets_sections1 tr'):
        label = row.css("th::text").get("").strip()
        value = row.css("td::text").get("").strip()
        if not value:
            value = row.css("td span::text").get("").strip()
        info_table[label] = value
    info_table['Customer Reviews'] = sel.xpath("//td[div[@id='averageCustomerReviews']]//span[@class='a-icon-alt']/text()").get()
    rank = sel.xpath("//tr[th[text()=' Best Sellers Rank ']]//td//text()").getall()
    info_table['Best Sellers Rank'] = ' '.join([text.strip() for text in rank if text.strip()])
    parsed['info_table'] = info_table
    return parsed


async def scrape_product(url: str) -> List[Dict]:
    """scrape Amazon.com product"""
    url = url.split("/ref=")[0]
    asin = url.split("/dp/")[-1]
    print(f"scraping product {url}")
    product_result = await SCRAPFLY.async_scrape(ScrapeConfig(
        url, 
        **BASE_CONFIG, 
        render_js=True, 
        wait_for_selector="#productDetails_detailBullets_sections1 tr",
    ))
    variants = [parse_product(product_result)]

    # if product has variants - we want to scrape all of them
    _variation_data = re.findall(r'dimensionValuesDisplayData"\s*:\s*({.+?}),\n', product_result.content)
    if _variation_data:
        variant_asins = [variant_asin for variant_asin in json.loads(_variation_data[0]) if variant_asin != asin]
        print(f"scraping {len(variant_asins)} variants: {variant_asins}")
        _to_scrape = [ScrapeConfig(f"https://www.amazon.com/dp/{asin}", **BASE_CONFIG) for asin in variant_asins]
        async for result in SCRAPFLY.concurrent_scrape(_to_scrape):
            variants.append(parse_product(result))
    return variants


async def main():
    product_data = await scrape_product(
        url = "https://www.amazon.com/PlayStation-5-Console-CFI-1215A01X/dp/B0BCNKKZ91/"
    )

    # save the results to a json file
    with open("product_data.json", "w", encoding="utf-8") as f:
        json.dump(product_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())