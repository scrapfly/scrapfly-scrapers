"""
This is an example web scraper for BestBuy.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import re
import os
import gzip
import json
import jmespath
from typing import Dict, List, Union
from parsel import Selector
from urllib.parse import urlencode, quote_plus
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass bestbuy.com web scraping blocking
    "unblocker": True,
    # set the proxy country to US
    "country": "US",
    "proxy_pool":"public_residential_pool",
    # "headers": {"cookie": "intl_splash=false"},
}


def parse_sitemaps(response: ScrapeApiResponse) -> List[str]:
    """parse links for bestbuy sitemap"""
    # decode the .gz file
    content = response.scrape_result["content"]
    bytes_data = content.read() if hasattr(content, "read") else content.encode("latin1")
    xml = str(gzip.decompress(bytes_data), "utf-8")
    selector = Selector(xml)
    # the sitemap namespace would hide its tags from the xpath
    selector.remove_namespaces()
    data = []
    for url in selector.xpath("//url/loc/text()"):
        data.append(url.get())
    return data


async def scrape_sitemaps(url: str) -> List[str]:
    """scrape link data from bestbuy sitemap"""
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    promo_urls = parse_sitemaps(response)
    log.success(f"scraped {len(promo_urls)} urls from sitemaps")
    return promo_urls


def refine_product(data: Dict) -> Dict:
    """refine the JSON product data"""
    parsed_product = {}
    specifications = data["shop-specifications"]["specifications"]["categories"]
    pricing = data["pricing"]["app"]["data"]["skuPriceDomain"]
    ratings = jmespath.search(
        """{
        featureRatings: aggregateSecondaryRatings,
        positiveFeatures: distillation.positiveFeatures[].{name: name, score: representativeQuote.score, totalReviewCount: totalReviewCount},
        negativeFeatures: distillation.negativeFeatures[].{name: name, score: representativeQuote.score, totalReviewCount: totalReviewCount}
        }""",
        data["reviews"]["app"],
    )
    faqs = []
    for item in data["faqs"]["app"]["questions"]["results"]:
        result = jmespath.search(
            """{
            sku: sku,
            questionTitle: questionTitle,
            answersForQuestion: answersForQuestion[].answerText
            }""",
            item,
        )
        faqs.append(result)

    # define the final parsed product
    parsed_product["specifications"] = specifications
    parsed_product["pricing"] = pricing
    parsed_product["ratings"] = ratings
    parsed_product["faqs"] = faqs

    return parsed_product


def extract_json(script: str) -> Dict:
    """extract JSON data from a script tag content"""
    start_index = script.find(".push(")
    brace_start = script.find("{", start_index)

    # find the JSON block
    brace_count = 0
    for i in range(brace_start, len(script)):
        if script[i] == "{":
            brace_count += 1
        elif script[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                brace_end = i + 1
                break

    raw_json = script[brace_start:brace_end]
    cleaned_json = raw_json.replace("undefined", "null")
    parsed_data = json.loads(cleaned_json)
    return parsed_data


def _extract_nested(data, keys, default=None):
    for key in keys:
        data = data.get(key, {})
    return data or default


def parse_product(response: ScrapeApiResponse) -> Dict:
    """parse product data from bestbuy product pages"""
    selector = response.selector
    data = {}

    product_scripts = selector.xpath("//script[contains(text(),'productBySkuId')]/text()").getall()
    for script_text in product_scripts:
        json_data = extract_json(script_text)
        if not json_data:
            continue

        for event in json_data.get("events", []):
            if event.get("type") != "next":
                continue
            product_data = _extract_nested(event, ["value", "data", "productBySkuId"])
            if not product_data:
                continue

            if not data.get("product-info") and product_data.get("brand") and product_data.get("whatItIs"):
                data["product-info"] = product_data
            if not data.get("product-features") and "features" in product_data:
                data["product-features"] = product_data.get("features")
            if not data.get("buying-options") and "buyingOptions" in product_data:
                data["buying-options"] = product_data.get("buyingOptions")
            if not data.get("product-faq") and "questions" in product_data:
                data["product-faq"] = product_data.get("questions")

    return data


async def scrape_products(urls: List[str], max_review_pages: int = 1) -> List[Dict]:
    """scrapy product data from bestbuy product pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG, render_js=True) for url in urls]
    data = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            product_data = parse_product(response)
            product_data["product_reviews"] = await scrape_reviews(
                product_data["product-info"]["skuId"], max_pages=max_review_pages
            )
            data.append(product_data)
        except:
            pass
            log.error("expired selectors or product page")

    log.success(f"scraped {len(data)} products from product pages")
    return data


def search_products_data(response: ScrapeApiResponse):
    """product data the page loaded for its search cards, by sku, and the number of results found: the search answer
    embedded in the page (full data for the first cards only) and the page's own item requests (one per card as it
    renders, with name, url, price and rating), for the cards the page had not finished rendering"""
    products, total_found = {}, None
    for script_text in response.selector.xpath("//script[contains(text(),'numFound')]/text()").getall():
        json_data = extract_json(script_text) or {}
        for event in json_data.get("events", []):
            search = _extract_nested(event, ["value", "data", "search"])
            if not search:
                continue
            total_found = total_found or search.get("numFound")
            for placement in (search.get("withBestMedia") or {}).get("placements") or []:
                for document in (placement.get("documentsGridView") or {}).get("sponsoredDocuments") or []:
                    product = document.get("product") or {}
                    if product.get("skuId") and product.get("price"):
                        products.setdefault(product["skuId"], product)
    for call in (response.scrape_result.get("browser_data") or {}).get("xhr_call") or []:
        if "PlpView_ProductListItem_Init" not in str(call.get("body")) or not (call.get("response") or {}).get("body"):
            continue
        try:
            product = json.loads(call["response"]["body"])["data"]["productBySkuId"] or {}
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        if product.get("skuId") and product.get("price"):
            products.setdefault(product["skuId"], product)
    return products, total_found


def parse_search(response: ScrapeApiResponse):
    """parse search data from search pages"""
    selector = response.selector
    data = []
    # the cards render in stages (shell, then name, then price) and some are still bare when the page is captured:
    # complete them from the product data the page itself loaded for them
    products, total_found = search_products_data(response)

    for item in selector.css(".product-grid-view-container li"):
        if item.css(".a-skeleton-shimmer").get():
            continue
        sku = item.xpath("@data-testid").get()
        product = products.get(sku) or {}
        product_price = product.get("price") or {}

        name = item.css(".product-title::attr(title)").get() or (product.get("name") or {}).get("short")

        link = item.css("a.product-list-item-link::attr(href)").get() or (product.get("url") or {}).get("pdp")

        price = None
        price_element = item.css('[data-testid="price-block-customer-price"] span::text').get()
        if price_element:
            price = re.sub(r'[^\d.]', '', price_element) or None
        if not price and product_price.get("customerPrice") is not None:
            price = f"{product_price['customerPrice']:.2f}"
        original_price = None
        original_price_elements = item.css('[data-testid="price-block-regular-price"] span::text').getall()
        for elem in original_price_elements:
            if '$' in elem:
                original_price = re.sub(r'[^\d.]', '', elem) or None
                break
        regular_price = product_price.get("displayableRegularPrice")
        if not original_price and regular_price and regular_price != product_price.get("customerPrice"):
            original_price = f"{regular_price:.2f}"

        rating = None
        rating_count = 0
        rating_text = item.css('div.c-ratings-reviews p.visually-hidden::text').get()
        if rating_text:
            m = re.search(r'Rating\s+([\d.]+)\s+out of\s+\d+\s+stars\s+with\s+([\d,]+)\s+reviews?', rating_text)
            if m:
                rating = m.group(1)
                rating_count = int(m.group(2).replace(',', ''))
        review_info = product.get("reviewInfo") or {}
        if rating is None and review_info.get("averageRating") is not None:
            rating = str(review_info["averageRating"])
            rating_count = review_info.get("reviewCount") or 0

        images = item.css("img[data-testid='product-image']::attr(srcset)").getall()

        if name and sku and price:
            data.append({
                "name": name,
                "link": link if (link and link.startswith('http')) else (f"https://www.bestbuy.com{link}" if link else None),
                "images": images,
                "sku": sku,
                "price": price,
                "original_price": original_price,
                "rating": rating,
                "rating_count": rating_count,
            })

    total_pages = 1
    cards = selector.css(".product-grid-view-container li")
    if cards:
        try:
            count_text = selector.css(".show-more-count-text::text").get()
            if count_text:
                count_matches = re.findall(r'([\d,]+) of ([\d,]+)', count_text)
                if count_matches:
                    page_size = int(count_matches[0][0].replace(',', ''))
                    total_count = int(count_matches[0][1].replace(',', ''))
                    if page_size:
                        total_pages = (total_count + page_size - 1) // page_size
            elif total_found:
                # the count text renders with the cards: before that, the embedded search answer has the total
                total_pages = (total_found + len(cards) - 1) // len(cards)
        except Exception as e:
            log.warning(f"Could not parse total pages: {e}")
            total_pages = 1

    return {"data": data, "total_pages": total_pages}


async def scrape_search(search_query: str, sort: Union["-bestsellingsort", "-Best-Discount"] = None, max_pages=None):
    """scrape search data from bestbuy search"""

    def form_search_url(page_number: int):
        """form the search url"""
        base_url = "https://www.bestbuy.com/site/searchpage.jsp?"
        # search parameters
        params = {"st": quote_plus(search_query)}
        if page_number > 1:
            params["cp"] = page_number
        if sort:
            params["sp"] = sort
        return base_url + urlencode(params)

    search_js_scenario = [
        {"wait": 2000},
        {"scroll": {"infinite": 2}},
        {"wait": 5000},
        {"scroll": {"infinite": 2}},
    ]
    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            form_search_url(1),
            render_js=True,
            rendering_wait=10000,
            auto_scroll=True,
            js_scenario=search_js_scenario,
            **BASE_CONFIG,
        )
    )
    data = parse_search(first_page)
    search_data = data["data"]
    total_pages = data["total_pages"]
    # the site sometimes answers a search with its "no results" layout (a recommendations carousel instead of the grid)
    if not search_data and first_page.selector.css("[class*='product-flexbox-noresults']"):
        raise ValueError(
            f"bestbuy.com answered the search for {search_query!r} with its no-results page instead of the product list"
        )
    # or with its error page ("We're unable to display products at the moment")
    error_text = first_page.selector.css("[data-component-name='ProductList'] .no-results-found h3::text").get()
    if not search_data and error_text:
        raise ValueError(
            f"bestbuy.com answered the search for {search_query!r} with its error page: {error_text.strip()!r}"
        )

    # get the number of total search pages to scrape
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    log.info(f"scraping search pagination, {total_pages - 1} more pages")
    # add the remaining pages to a scraping list to scrape them concurrently
    to_scrape = [
        ScrapeConfig(
            form_search_url(page_number),
            render_js=True,
            rendering_wait=10000,
            auto_scroll=True,
            js_scenario=search_js_scenario,
            **BASE_CONFIG,
        )
        for page_number in range(2, total_pages + 1)
    ]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_search(response)["data"]
        search_data.extend(data)

    log.success(f"scraped {len(search_data)} products from search pages")
    return search_data


def parse_reviews(response: ScrapeApiResponse) -> List[Dict]:
    """parse review data from the review API responses"""
    data = json.loads(response.scrape_result["content"])
    total_count = data["totalPages"]
    review_data = data["topics"]
    return {"data": review_data, "total_count": total_count}


async def scrape_reviews(skuid: int, max_pages: int = None) -> List[Dict]:
    """scrape review data from the reviews API"""
    log.info(f"scraping first review page for skuid: {skuid}")
    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            f"https://www.bestbuy.com/ugc/v2/reviews?page=1&pageSize=20&sku={skuid}&sort=MOST_RECENT", **BASE_CONFIG
        )
    )
    data = parse_reviews(first_page)
    review_data = data["data"]
    total_count = data["total_count"]

    # get the number of total review pages to scrape
    if max_pages and max_pages < total_count:
        total_count = max_pages

    log.info(f"scraping reviews pagination, {total_count - 1} more pages")
    # add the remaining pages to a scraping list to scrape them concurrently
    to_scrape = [
        ScrapeConfig(
            f"https://www.bestbuy.com/ugc/v2/reviews?page={page_number}&pageSize=20&sku={skuid}&sort=MOST_RECENT",
            **BASE_CONFIG,
        )
        for page_number in range(2, total_count + 1)
    ]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        data = parse_reviews(response)["data"]
        review_data.extend(data)

    log.success(f"scraped {len(review_data)} reviews from the reviews API")
    return review_data
