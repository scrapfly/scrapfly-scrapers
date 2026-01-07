# https://gist.github.com/scrapfly-dev/694edd771381ea2b1cdf1a2ffcd32c88
import os
import math
import json
import asyncio

from typing import Dict, List
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

BASE_CONFIG = {
    "asp": True,
    "country": "US",
}

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

def strip_text(text):
    """remove extra spaces while handling None values"""
    if text != None:
        text = text.strip()
    return text


def parse_search(response: ScrapeApiResponse) -> Dict:
    """parse data from Etsy search pages"""
    selector = response.selector
    data = []
    script = json.loads(selector.xpath("//script[@type='application/ld+json']/text()").get())
    # get the total number of pages
    total_listings = script["numberOfItems"]
    total_pages = math.ceil(total_listings / 48)
    for product in selector.xpath("//div[@data-search-results-lg]/ul/li[div[@data-appears-component-name]]"):
        link = product.xpath(".//a[contains(@class, 'v2-listing-card')]/@href").get()
        rate = product.xpath(".//span[contains(@class, 'review_stars')]/span/text()").get()
        number_of_reviews = strip_text(product.xpath(".//div[contains(@aria-label,'star rating')]/p/text()").get())
        if number_of_reviews:
            number_of_reviews = number_of_reviews.replace("(", "").replace(")", "")
            number_of_reviews = (
                int(number_of_reviews.replace("k", "").replace(".", "")) * 10
                if "k" in number_of_reviews
                else number_of_reviews
            )
        price = product.xpath(".//span[@class='currency-value']/text()").get()
        original_price = product.xpath(".//span[contains(text(),'Original Price')]/text()").get()
        discount = strip_text(product.xpath(".//span[contains(text(),'off')]/text()").get())
        seller = product.xpath(".//span[contains(text(),'From shop')]/text()").get()
        currency = product.xpath(".//span[@class='currency-symbol']/text()").get()
        data.append(
            {
                "productLink": "/".join(link.split("/")[:5]) if link else None,
                "productTitle": strip_text(
                    product.xpath(".//h3[contains(@class, 'v2-listing-card__titl')]/@title").get()
                ),
                "productImage": product.xpath("//img[@data-listing-card-listing-image]/@src").get(),
                "seller": seller.replace("From shop ", "") if seller else None,
                "listingType": (
                    "Paid listing" if product.xpath(".//span[@data-ad-label='Ad by Etsy seller']") else "Free listing"
                ),
                "productRate": float(rate.strip()) if rate else None,
                "numberOfReviews": int(number_of_reviews) if number_of_reviews else None,
                "freeShipping": (
                    "Yes" if product.xpath(".//span[contains(text(),'Free shipping')]/text()").get() else "No"
                ),
                "productPrice": float(price.replace(",", "")) if price else None,
                "priceCurrency": currency,
                "originalPrice": float(original_price.split(currency)[-1].strip().replace(",", "")) if original_price else "No discount",
                "discount": discount if discount else "No discount",
            }
        )
    return {"search_data": data, "total_pages": total_pages}


async def scrape_search(url: str, max_pages: int = None) -> List[Dict]:
    """scrape product listing data from Etsy search pages"""
    print("scraping the first search page")
    # etsy search pages are dynaminc, requiring render_js enabled
    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url,
            wait_for_selector="//div[@data-search-pagination]",
            render_js=True,
            auto_scroll=True,
            proxy_pool="public_residential_pool",
            **BASE_CONFIG,
        )
    )
    data = parse_search(first_page)
    search_data = data["search_data"]

    # get the number of total pages to scrape
    total_pages = data["total_pages"]
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    print(f"scraping search pagination ({total_pages - 1} more pages)")
    # add the remaining search pages in a scraping list
    other_pages = [
        ScrapeConfig(
            url + f"&page={page_number}",
            wait_for_selector="//div[@data-search-pagination]",
            render_js=True,
            proxy_pool="public_residential_pool",
            **BASE_CONFIG,
        )
        for page_number in range(2, total_pages + 1)
    ]
    # scrape the remaining search pages concurrently
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        # try:
        data = parse_search(response)
        search_data.extend(data["search_data"])
        # except Exception as e:
        #     print(f"failed to scrape search page: {e}")
        #     pass
    print(f"scraped {len(search_data)} product listings from search")
    return search_data


async def main():
    search_data = await scrape_search(url="https://www.etsy.com/search?q=wood+laptop+stand", max_pages=3)

    # save the results to a json file
    with open("search_data.json", "w", encoding="utf-8") as file:
        json.dump(search_data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())
