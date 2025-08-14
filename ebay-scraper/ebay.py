"""
This is an example web scraper for Ebay.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-ebay/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import json
import math
import os
from collections import defaultdict
from typing import Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import dateutil
from nested_lookup import nested_lookup
from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Ebay.com requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "country": "US",  # change country for geo details like currency and shipping
    "lang": ["en-US"],
}


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
    # example variant entry:
    # {
    #     'id': '662315637173',
    #     'Model': 'Apple iPhone 11 Pro Max',
    #     'Storage Capacity': '64 GB',
    #     'Color': 'Gold',
    #     'price_original': 469,
    #     'price_original_currency': 'CAD',
    #     'price_converted': 341.55,
    #     'price_converted_currency': 'USD',
    #     'out_of_stock': False
    # }
    return results


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
    page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    product = parse_product(page)
    product["variants"] = parse_variants(page)
    return product


def parse_search(result: ScrapeApiResponse) -> List[Dict]:
    """Parse ebay.com search result page for product previews"""
    previews = []
    best_selling_boxes = result.selector.xpath(
        "//*[*[h2[contains(text(),'Best selling products')]]]//li[contains(@class, 's-item')]"
    )
    best_selling_html_set = set([b.get() for b in best_selling_boxes])

    for box in result.selector.css(".srp-results li.s-item"):
        if box.get() in best_selling_html_set:
            continue  # skip boxes inside the best selling container

        css = lambda css: box.css(css).get("").strip() or None  # get first CSS match
        css_all = lambda css: box.css(css).getall()  # get all CSS matches
        css_re = lambda css, pattern: box.css(css).re_first(pattern, default="").strip()  # get first css regex match
        css_int = lambda css: int(box.css(css).re_first(r"(\d+)", default="0")) if box.css(css) else None
        css_float = lambda css: float(box.css(css).re_first(r"(\d+\.*\d*)", default="0.0")) if box.css(css) else None
        auction_end = css_re(".s-item__time-end::text", r"\((.+?)\)") or None
        if auction_end:
            auction_end = dateutil.parser.parse(auction_end.replace("Today", ""))
        item = {
            "url": css("a.s-item__link::attr(href)").split("?")[0],
            "title": css(".s-item__title span::text"),
            "price": css(".s-item__price::text"),
            "shipping": css_float(".s-item__shipping::text"),
            "auction_end": auction_end,
            "bids": css_int(".s-item__bidCount::text"),
            "location": css(".s-item__itemLocation::text"),
            "subtitles": css_all(".s-item__subtitle::text"),
            "condition": css(".SECONDARY_INFO::text"),
            "photo": css("img::attr(data-src)") or css("img::attr(src)"),
            "rating": css_float(".s-item__reviews .clipped::text"),
            "rating_count": css_int(".s-item__reviews-count span::text"),
        }
        previews.append(item)
    return previews


def _get_url_parameter(url: str, param: str, default=None) -> Optional[str]:
    """get url parameter value"""
    query_params = dict(parse_qsl(urlparse(url).query))
    return query_params.get(param) or default


def _update_url_param(url: str, **params):
    """adds url parameters or replaces them with new values"""
    parsed_url = urlparse(url)
    query_params = dict(parse_qsl(parsed_url.query))
    query_params.update(params)
    updated_url = parsed_url._replace(query=urlencode(query_params))
    return urlunparse(updated_url)


async def scrape_search(url: str, max_pages: Optional[int] = None) -> List[Dict]:
    """Scrape Ebay's search for product preview data for given"""
    log.info("Scraping search for {}", url)

    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    results = parse_search(first_page)
    # find total amount of results for concurrent pagination
    total_results = first_page.selector.css(".srp-controls__count-heading>span::text").get()
    total_results = int(total_results.replace(",", "").replace(".", ""))
    items_per_page = int(_get_url_parameter(first_page.context["url"], "_ipg", default=60))
    total_pages = math.ceil(total_results / items_per_page)
    if max_pages and total_pages > max_pages:
        total_pages = max_pages
    other_pages = [
        ScrapeConfig(_update_url_param(first_page.context["url"], _pgn=i), **BASE_CONFIG)
        for i in range(2, total_pages + 1)
    ]
    log.info("Scraping search pagination of {} total pages for {}", len(other_pages), url)
    async for result in SCRAPFLY.concurrent_scrape(other_pages):
        if not isinstance(result, ScrapflyScrapeError):
            try:
                results.extend(parse_search(result))
            except Exception as e:
                log.error(f"failed to parse search: {result.context['url']}: {e}")
        else:
            log.error(f"failed to scrape {result.api_response.config['url']}, got: {result.message}")
    return results
