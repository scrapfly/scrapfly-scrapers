# https://gist.github.com/scrapfly-dev/dc8e6fc4201d7d04c5bd88dd86c6c1b4
import json
import math
import os
import re
import asyncio

from typing import Dict, List
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    # Us locale, apply localization settings from the browser and then copy the aep_usuc_f cookie from devtools
    "headers": {
        "cookie": "aep_usuc_f=site=glo&province=&city=&c_tp=USD&region=US&b_locale=en_US&ae_u_p_s=2"
    }
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def parse_category_page(response: ScrapeApiResponse):
    """Parse category page response for product preview results"""
    selector = response.selector
    script_data = selector.xpath('//script[contains(.,"_init_data_=")]')
    json_data = json.loads(script_data.re(r"_init_data_\s*=\s*{\s*data:\s*({.+}) }")[0])
    json_data = json_data['data']['root']['fields']
    product_data = json_data['mods']['itemList']['content']
    total_results = json_data['pageInfo']['totalResults']
    page_size = json_data['pageInfo']['pageSize']
    total_pages = int(math.ceil(total_results / page_size))
    return {
        'product_data': product_data,
        'total_pages': total_pages
    }


async def find_aliexpress_products(url: str, max_pages: int) -> List[Dict]:
    """Find Aliexpress products from category pages"""
    print(f"finding products from category page: {url}")
    first_page_result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    first_page_data = parse_category_page(first_page_result)
    all_product_data = first_page_data['product_data']
    total_pages = first_page_data['total_pages'] - 1 # exclude the first page from the count

    if max_pages is None:
        max_pages = total_pages
    print('found {} pages, but only scraping {} pages'.format(total_pages, max_pages))

    remaining_pages = [
        ScrapeConfig(url + f"?page={page}", **BASE_CONFIG)
        for page in range(2, max_pages + 1)
    ]

    async for result in SCRAPFLY.concurrent_scrape(remaining_pages):
        product_data = parse_category_page(result)['product_data']
        all_product_data.extend(product_data)
    
    print(f"discovered {len(all_product_data)} products from {url}")
    return all_product_data


async def main():
    data = await find_aliexpress_products(
        url="https://www.aliexpress.com/category/5090301/cellphones.html",
        # if max_pages is not provided, all pagination pages will be scraped
        max_pages=2
    )

    # save the data into a json file
    with open("category_products.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())
