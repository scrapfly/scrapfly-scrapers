# https://gist.github.com/scrapfly-dev/77587ae3c93a3cea3d27fcd583616edd
import json
import os
import re
import asyncio

from typing import Dict, List
from collections import defaultdict
from nested_lookup import nested_lookup
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "lang": ["en-US"]
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def _find_json_objects(text: str, decoder=json.JSONDecoder()):
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

def parse_variants(result: ScrapeApiResponse) -> dict:
    """
    Parse variant data from Ebay's listing page of a product with variants.
    This data is located in a js variable MSKU hidden in a <script> element.
    """
    script = result.selector.xpath('//script[contains(., "MSKU")]/text()').get()
    if not script:
        return {}
    all_data = list(_find_json_objects(script))
    msku_data = nested_lookup("MSKU", all_data)
    if not msku_data:
        return {}  # No variants found for this product
    data = msku_data[0]
    # First retrieve names for all selection options (e.g. Model, Color)
    selection_names = {}
    for menu in data["selectMenus"]:
        for id_ in menu["menuItemValueIds"]:
            selection_names[id_] = menu["displayLabel"]
    # example selection name entry:
    # {0: 'Model', 1: 'Color', ...}

    # Then, find all selection combinations:
    selections = []
    for v in data["menuItemMap"].values():
        selections.append(
            {
                "name": v["valueName"],
                "variants": v["matchingVariationIds"],
                "label": selection_names[v["valueId"]],
            }
        )
    # example selection entry:
    # {'name': 'Gold', 'variants': [662315637181, 662315637177, 662315637173], 'label': 'Color'}

    # Finally, extract variants and apply selection details to each
    results = []
    variant_data = nested_lookup("variationsMap", data)[0]
    for id_, variant in variant_data.items():
        result = defaultdict(list)
        result["id"] = id_
        for selection in selections:
            if int(id_) in selection["variants"]:
                result[selection["label"]] = selection["name"]
        result["price_original"] = variant["binModel"]["price"]["value"]["convertedFromValue"]
        result["price_original_currency"] = variant["binModel"]["price"]["value"]["convertedFromCurrency"]
        result["price_converted"] = variant["binModel"]["price"]["value"]["value"]
        result["price_converted_currency"] = variant["binModel"]["price"]["value"]["currency"]
        result["out_of_stock"] = variant["quantity"]["outOfStock"]
        results.append(dict(result))
    return results


async def scrape_product_varaiants(url: str) -> Dict:
    """Scrape ebay.com product listing page for product variants data"""
    print(f"scraping product variants: {url}")
    page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    variant_data = parse_variants(page)
    return variant_data


async def main():
    variant_data = await scrape_product_varaiants("https://www.ebay.com/itm/393531906094")

    # save the results to a json file
    with open("variant_data.json", "w", encoding="utf-8") as f:
        json.dump(variant_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())