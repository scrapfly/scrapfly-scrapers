"""
This is an example web scraper for g2.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import re
import math
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from typing import Dict, List, Literal
from loguru import logger as log
from urllib.parse import urljoin

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass G2 web scraping blocking
    "asp": True,
    # set the poxy location to US
    "country": "US",
}


def parse_search_page(response: ScrapeApiResponse):
    """Parse company data from search pages with updated selectors."""
    try:
        selector = response.selector
    except Exception as e:
        print(f"Failed to create selector: {e}")
        return {"search_data": [], "total_pages": 0}

    data = []

    # Extract total results count
    total_results_text = selector.xpath("//div[contains(text(), 'Products')]/following-sibling::div/text()").get()
    total_results = int(re.search(r"\((\d+)\)", total_results_text).group(1)) if total_results_text else 0

    _search_page_size = 20
    total_pages = math.ceil(total_results / _search_page_size) if total_results else 0

    # Main selector for each product card
    for result in selector.xpath("//section[.//a[contains(@href, '/products/')]]"):
        name = result.xpath(".//div[contains(@class, 'elv-text-lg')]/text()").get()

        # CORRECTED LINE: Use urljoin() from urllib.parse
        relative_link = result.xpath(".//div[contains(@class, 'elv-text-lg')]/parent::a/@href").get()
        link = urljoin(response.request.url, relative_link)

        image = result.xpath(".//img[@itemprop='image']/@data-deferred-image-src").get()

        raw_rate = result.xpath(".//label[contains(text(), '/5')]/text()").get()
        rate = float(raw_rate.split("/")[0]) if raw_rate else None

        raw_reviews = result.xpath(".//a[contains(@href, '#reviews')]//label[not(contains(text(), '/5'))]/text()").get()
        reviews_number = int(raw_reviews.strip("()")) if raw_reviews else None

        description_parts = result.xpath(".//div[div[contains(text(), 'Product Description')]]/p//text()").getall()
        description = "".join(description_parts).strip() if description_parts else None

        categories = result.xpath(".//aside//div[contains(@class, 'elv-whitespace-nowrap')]/text()").getall()

        if not name:
            continue

        data.append(
            {
                "name": name.strip() if name else None,
                "link": link,
                "image": image,
                "rate": rate,
                "reviewsNumber": reviews_number,
                "description": description if description else None,
                "categories": [cat.strip() for cat in categories],
            }
        )

    return {"search_data": data, "total_pages": total_pages}


async def scrape_search(url: str, max_scrape_pages: int = None) -> List[Dict]:
    """scrape company listings from search pages"""
    log.info(f"scraping search page {url}")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_search_page(first_page)
    search_data = data["search_data"]
    total_pages = data["total_pages"]

    # get the total number of pages to scrape
    if max_scrape_pages and max_scrape_pages < total_pages:
        total_pages = max_scrape_pages

    # scrape the remaining search pages concurrently and remove the successful request URLs
    log.info(f"scraping search pagination, remaining ({total_pages - 1}) more pages")
    remaining_urls = [url + f"&page={page_number}" for page_number in range(2, total_pages + 1)]
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in remaining_urls]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            data = parse_search_page(response)
            search_data.extend(data["search_data"])
            # remove the successful requests from the URLs list
            remaining_urls.remove(response.context["url"])
        except Exception as e:  # catch any exception
            log.error(f"Error encountered: {e}")
            continue

    # try again with the blocked requests if any using headless browsers and residential proxies
    if len(remaining_urls) != 0:
        log.debug(
            f"{len(remaining_urls)} requests are blocked, trying again with render_js enabled and residential proxies"
        )
        try:
            failed_requests = [
                ScrapeConfig(
                    url,
                    **BASE_CONFIG,
                    render_js=True,
                    proxy_pool="public_residential_pool",
                )
                for url in remaining_urls
            ]
            async for response in SCRAPFLY.concurrent_scrape(failed_requests):
                data = parse_search_page(response)
                search_data.extend(data["search_data"])
        except Exception as e:  # catching any exception
            log.error(f"Error encountered: {e}")
            pass
    log.success(f"scraped {len(search_data)} company listings from G2 search pages with the URL {url}")
    return search_data


def parse_review_page(response: ScrapeApiResponse):
    """parse reviews data from G2 company pages"""
    selector = response.selector

    # Corrected selector for total reviews
    total_reviews_text = selector.xpath("//h3[contains(text(), 'DigitalOcean Reviews')]/text()").get()
    if total_reviews_text:
        total_reviews = int(total_reviews_text.split()[0])
        # Updated: The page now shows 10 reviews, not 25
        _review_page_size = 10
        total_pages = math.ceil(total_reviews / _review_page_size)
    else:
        total_reviews = None
        total_pages = 0

    data = []
    # Corrected main review container selector from 'div' to 'article'
    for review in selector.xpath("//article[.//div[@itemprop='reviewBody']]"):
        author_name = review.xpath(".//div[@itemprop='author']/meta[@itemprop='name']/@content").get()
        author_profile = review.xpath(".//div[contains(@class, 'avatar')]/parent::a/@href").get()

        # Author details have a new, less structured format
        author_details = review.xpath(
            ".//div[div[@itemprop='author']]//div[contains(@class, 'elv-text-subtle')]/text()"
        ).getall()
        author_position = author_details[0] if author_details and len(author_details) > 0 else None
        author_company_size = next((detail for detail in author_details if "emp." in detail), None)

        # Corrected selector for review tags
        review_tags = review.xpath(
            ".//div[contains(@class, 'gap-3') and contains(@class, 'flex-wrap')]//label/text()"
        ).getall()

        review_date = review.xpath(".//meta[@itemprop='datePublished']/@content").get()
        # Corrected selector for review rate using the reliable itemprop meta tag
        review_rate = review.xpath(".//span[@itemprop='reviewRating']/meta[@itemprop='ratingValue']/@content").get()
        review_title = review.xpath(".//div[@itemprop='name']//text()").get()

        # Corrected selectors for review likes and dislikes
        review_likes_parts = review.xpath(
            ".//section[div[contains(text(), 'What do you like best')]]/p//text()"
        ).getall()
        review_likes = "".join(review_likes_parts).replace("Review collected by and hosted on G2.com.", "").strip()

        review_dislikes_parts = review.xpath(
            ".//section[div[contains(text(), 'What do you dislike')]]/p//text()"
        ).getall()
        review_dislikes = (
            "".join(review_dislikes_parts).replace("Review collected by and hosted on G2.com.", "").strip()
        )

        data.append(
            {
                "author": {
                    "authorName": author_name.strip() if author_name else None,
                    "authorProfile": author_profile,
                    "authorPosition": (author_position.strip() if author_position else None),
                    "authorCompanySize": (author_company_size.strip() if author_company_size else None),
                },
                "review": {
                    "reviewTags": [tag.strip() for tag in review_tags if tag.strip()],
                    "reviewData": review_date,
                    "reviewRate": float(review_rate) if review_rate else None,
                    "reviewTitle": (review_title.replace('"', "").strip() if review_title else None),
                    "reviewLikes": review_likes,
                    "reviewDilikes": review_dislikes,  # Typo from original code, kept for consistency
                },
            }
        )

    return {"total_pages": total_pages, "reviews_data": data}


async def scrape_reviews(url: str, max_review_pages: int = None) -> List[Dict]:
    """scrape company reviews from G2 review pages"""
    log.info(f"scraping first review page from company URL {url}")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_review_page(first_page)
    reviews_data = data["reviews_data"]
    total_pages = data["total_pages"]

    # get the number of total review pages to scrape
    if max_review_pages and max_review_pages < total_pages:
        total_pages = max_review_pages

    # scrape the remaining review pages
    log.info(f"scraping reviews pagination, remaining ({total_pages - 1}) more pages")
    remaining_urls = [url + f"?page={page_number}" for page_number in range(2, total_pages + 1)]
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in remaining_urls]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            data = parse_review_page(response)
            reviews_data.extend(data["reviews_data"])
            remaining_urls.remove(response.context["url"])
        except Exception as e:  # catch any exception
            log.error(f"Error encountered: {e}")
            continue

    if len(remaining_urls) != 0:
        log.debug(
            f"{len(remaining_urls)} requests are blocked, trying again with render_js enabled and residential proxies"
        )
        try:
            failed_requests = [
                ScrapeConfig(
                    url,
                    **BASE_CONFIG,
                    render_js=True,
                    proxy_pool="public_residential_pool",
                )
                for url in remaining_urls
            ]
            async for response in SCRAPFLY.concurrent_scrape(failed_requests):
                data = parse_search_page(response)
                reviews_data.extend(data["reviews_data"])
        except Exception as e:  # catch any exception
            log.error(f"Error encountered: {e}")
            pass
    log.success(f"scraped {len(reviews_data)} company reviews from G2 review pages with the URL {url}")
    return reviews_data


def parse_alternatives(response: ScrapeApiResponse):
    """parse G2 alternative pages"""
    try:
        selector = response.selector
    except:
        pass
    data = []
    for alt in selector.xpath("//div[contains(@class, 'product-listing--competitor')]"):
        sponsored = alt.xpath(".//strong[text()='Sponsored']").get()
        if sponsored:  # ignore sponsored cards
            continue
        name = alt.xpath(".//div[@itemprop='name']/text()").get()
        link = alt.xpath(".//h3/a[contains(@class, 'link')]/@href").get()
        ranking = alt.xpath(".//div[@class='product-listing__number']/text()").get()
        number_of_reviews = alt.xpath(".//div[div[contains(@class,'stars')]]/span/text()").get()  # clean this
        rate = alt.xpath(".//div[div[contains(@class,'stars')]]/span/span/text()").get()
        description = alt.xpath(".//div[@data-max-height-expand-type]/p/text()").get()
        data.append(
            {
                "name": name,
                "link": link,
                "ranking": ranking,
                "numberOfReviews": (int(number_of_reviews[1:-1].replace(",", "")) if number_of_reviews else None),
                "rate": float(rate.strip()) if rate else None,
                "description": description,
            }
        )
    return data


async def scrape_alternatives(
    product: str,
    alternatives: Literal["small-business", "mid-market", "enterprise"] = "",
) -> Dict:
    """scrape product alternatives from G2 alternative pages"""
    # the default alternative is top 10, which takes to argument
    url = f"https://www.g2.com/products/{product}/competitors/alternatives/{alternatives}"
    log.info(f"scraping alternative page {url}")
    try:
        response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
        data = parse_alternatives(response)
    except Exception as e:  # Catching any exception
        log.error(f"Error encountered: {e}, trying")
        pass
    if not data:
        log.debug("request is blocked, trying again with render_js enabled and residential proxies")
        try:
            response = await SCRAPFLY.async_scrape(
                ScrapeConfig(
                    url,
                    **BASE_CONFIG,
                    render_js=True,
                    proxy_pool="public_residential_pool",
                )
            )
            data = parse_alternatives(response)
        except:
            return
    log.success(f"scraped {len(data)} company alternatives from G2 alternative pages")
    return data
