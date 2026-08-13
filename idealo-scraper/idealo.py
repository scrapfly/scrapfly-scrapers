"""
This is an example web scraper for idealo.de.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import re
import json
from urllib.parse import urljoin, urlencode
from typing import List, Optional, TypedDict

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "DE",
    "render_js": True,
    "proxy_pool": "public_residential_pool",
}

LOAD_MORE_JS = """
const clickUntilGone = async () => {
  while (true) {
    const btn = document.querySelector('button.productOffers-listLoadMore');
    if (!btn) break;
    btn.click();
    await new Promise(r => setTimeout(r, 500));
  }
};
await clickUntilGone();
"""

BASE_URL = "https://www.idealo.de"
SEARCH_PAGE_SIZE = 15


class IdealoOffer(TypedDict):
    shop_name: str
    shop_url: Optional[str]
    shop_rating: Optional[str]
    shop_rating_count: Optional[int]
    price: Optional[float]
    currency: str
    delivery_info: Optional[str]
    merchant_name: Optional[str]
    url: str


class IdealoProduct(TypedDict):
    product_id: Optional[str]
    name: Optional[str]
    brand: Optional[str]
    url: str
    image: Optional[str]
    description: Optional[str]
    rating: Optional[float]
    rating_count: Optional[int]
    low_price: Optional[float]
    high_price: Optional[float]
    currency: Optional[str]
    offer_count: Optional[int]
    offers: List[IdealoOffer]


class IdealoListingItem(TypedDict):
    product_id: Optional[str]
    name: Optional[str]
    url: Optional[str]
    image: Optional[str]
    price: Optional[float]
    currency: str
    offer_count: Optional[int]
    shop_name: Optional[str]


class IdealoManufacturer(TypedDict):
    name: Optional[str]
    description: Optional[str]
    url: str
    result_count: Optional[int]
    products: List[IdealoListingItem]


def _parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    cleaned = text.replace("\xa0", " ").replace("€", "").replace(" ", "")
    match = re.search(r"[\d.]+,\d+|\d+", cleaned)
    if not match:
        return None
    try:
        return float(match.group(0).replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _parse_int(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    match = re.search(r"[\d.]+", text.replace("\xa0", " ").replace(" ", ""))
    if not match:
        return None
    try:
        return int(match.group(0).replace(".", ""))
    except ValueError:
        return None


def _parse_listing_item(card) -> IdealoListingItem:
    href = card.css('a[href*="OffersOfProduct"]::attr(href)').get()
    name = card.css('[class*="sr-productSummary__title"]::text').get()
    shop_name = card.css('[class*="sr-singleOffer__shopName"] span::text').get()
    wishlist_raw = card.css("[data-wishlist-heart]::attr(data-wishlist-heart)").get()
    wishlist = json.loads(wishlist_raw) if wishlist_raw else {}

    product_id = wishlist.get("id")
    if not product_id and href:
        match = re.search(r"/OffersOfProduct/(\d+)", href)
        product_id = match.group(1) if match else None

    return IdealoListingItem(
        product_id=product_id,
        name=name.strip() if name else None,
        url=urljoin(BASE_URL, href) if href else None,
        image=card.css('[class*="sr-resultItemTile__image"]::attr(src)').get(),
        price=_parse_price("".join(card.css('[class*="sr-detailedPriceInfo__price"] ::text').getall())),
        currency="EUR",
        offer_count=_parse_int(card.css('[class*="sr-detailedPriceInfo__offerCount"]::text').get()),
        shop_name=shop_name.strip() if shop_name else None,
    )


def _parse_total_pages(sel) -> int:
    pages = []
    pagination = sel.css('[class*="sr-pagination"]')
    for value in pagination.css("[aria-label]::attr(aria-label)").getall():
        if value.strip().isdigit():
            pages.append(int(value.strip()))
    for value in pagination.css('[class*="sr-pageElement"]::text, [class*="sr-textElement"]::text').getall():
        if value.strip().isdigit():
            pages.append(int(value.strip()))
    return max(pages) if pages else 1


def parse_search(response: ScrapeApiResponse) -> dict:
    """parse search listings from idealo.de"""
    sel = response.selector
    results = [_parse_listing_item(card) for card in sel.css('[class*="sr-resultList__item"]')]
    return {"results": results, "total_pages": _parse_total_pages(sel)}


def parse_manufacturer(response: ScrapeApiResponse) -> IdealoManufacturer:
    """parse manufacturer listing data from idealo.de"""
    sel = response.selector
    name = sel.css("h1::text").get()
    return IdealoManufacturer(
        name=name.strip() if name else None,
        description=sel.css('meta[name="description"]::attr(content)').get(),
        url=response.context["url"],
        result_count=_parse_int(sel.css('[class*="sr-resultTitle__resultCount"]::text').get()),
        products=[_parse_listing_item(card) for card in sel.css('[class*="sr-resultList__item"]')],
    )


def _parse_offers(sel) -> List[IdealoOffer]:
    offers = []
    for li in sel.css("li.productOffers-listItem"):
        mtrx_raw = li.attrib.get("data-mtrx-click")
        mtrx = json.loads(mtrx_raw) if mtrx_raw else {}
        mtrx_products = mtrx.get("products") or [{}]

        shop_name_raw = li.css(".productOffers-listItemOfferShopV2LogoLink::attr(data-shop-name)").get()
        shop_name = mtrx.get("shop_name") or (
            shop_name_raw.split(" - Shop aus")[0].strip() if shop_name_raw else None
        )
        url = li.css("a.productOffers-listItemOfferCtaLeadout::attr(href)").get() or li.css(
            "a.productOffers-listItemTitle::attr(href)"
        ).get()
        if not shop_name or not url:
            continue

        price = mtrx_products[0].get("price")
        if price is None:
            price = _parse_price(li.css(".productOffers-listItemOfferPrice::text").get())

        delivery = li.css(".productOffers-listItemOfferDeliveryStatusDatesRange::text").get()
        merchant = li.css(".productOffers-listItemOfferShopV2MarketPlaceMerchantName a::text").get()
        rating_count = li.css(".productOffers-listItemOfferShopV2NORatings--numberOfRatings::text").get()

        offers.append(
            IdealoOffer(
                shop_name=shop_name,
                shop_url=li.css(".productOffers-listItemOfferShopV2StarsLink::attr(href)").get(),
                shop_rating=li.css(".productOffers-listItemOfferShopV2Stars b::text").get(),
                shop_rating_count=_parse_int(rating_count),
                price=price,
                currency="EUR",
                delivery_info=delivery.strip() if delivery else None,
                merchant_name=merchant.strip() if merchant else None,
                url=urljoin(BASE_URL, url),
            )
        )
    return offers


def parse_product(response: ScrapeApiResponse) -> IdealoProduct:
    """parse product data from idealo.de product pages"""
    sel = response.selector
    raw = sel.css('script[data-testid="Product"]::text').get()
    data = json.loads(raw) if raw else {}

    match = re.search(r"/OffersOfProduct/(\d+)", response.context["url"])
    images = data.get("image") or []
    rating = data.get("aggregateRating") or {}
    offer_summary = data.get("offers") or {}

    return IdealoProduct(
        product_id=match.group(1) if match else data.get("sku"),
        name=data.get("name"),
        brand=(data.get("brand") or {}).get("name"),
        url=data.get("url") or response.context["url"],
        image=images[0] if images else None,
        description=data.get("description"),
        rating=rating.get("ratingValue"),
        rating_count=rating.get("ratingCount"),
        low_price=offer_summary.get("lowPrice"),
        high_price=offer_summary.get("highPrice"),
        currency=offer_summary.get("priceCurrency"),
        offer_count=offer_summary.get("offerCount"),
        offers=_parse_offers(sel),
    )


async def scrape_products(urls: List[str]) -> List[IdealoProduct]:
    """scrape product pages from idealo.de"""
    products = []
    to_scrape = [ScrapeConfig(url, js=LOAD_MORE_JS, **BASE_CONFIG) for url in urls]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        if isinstance(response, ScrapflyScrapeError):
            log.error(f"failed to scrape product: {response}")
            continue
        products.append(parse_product(response))
    log.success(f"scraped {len(products)} products")
    return products


async def scrape_search(query: str, max_pages: int = 3) -> List[IdealoListingItem]:
    """scrape search listings from idealo.de"""
    params = urlencode({"q": query})
    first_url = f"{BASE_URL}/preisvergleich/MainSearchProductCategory.html?{params}"
    log.info(f"scraping the first search page {first_url}")

    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(first_url, wait_for_selector='[class*="sr-resultList"]', **BASE_CONFIG)
    )
    data = parse_search(first_page)
    results = data["results"]
    total_pages = min(data["total_pages"], max_pages)
    log.info(f"found {data['total_pages']} search pages, scraping {total_pages}")

    if total_pages > 1:
        other_pages = []
        for page in range(2, total_pages + 1):
            offset = (page - 1) * SEARCH_PAGE_SIZE
            url = f"{BASE_URL}/preisvergleich/MainSearchProductCategory/100I16-{offset}.html?{params}"
            other_pages.append(ScrapeConfig(url, wait_for_selector='[class*="sr-resultList"]', **BASE_CONFIG))

        async for response in SCRAPFLY.concurrent_scrape(other_pages):
            if isinstance(response, ScrapflyScrapeError):
                log.error(f"failed to scrape search page: {response}")
                continue
            results.extend(parse_search(response)["results"])

    log.success(f"scraped {len(results)} search results")
    return results


async def scrape_manufacturer(url: str) -> IdealoManufacturer:
    """scrape a manufacturer listing page from idealo.de"""
    log.info(f"scraping manufacturer page {url}")
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, wait_for_selector='[class*="sr-resultList"]', **BASE_CONFIG)
    )
    manufacturer = parse_manufacturer(response)
    log.success(f"scraped manufacturer {manufacturer['name']} with {len(manufacturer['products'])} products")
    return manufacturer
