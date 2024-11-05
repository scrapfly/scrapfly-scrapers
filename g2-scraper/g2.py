"""
This is an example web scraper for g2.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import math
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse
from typing import Dict, List, Literal
from loguru import logger as log

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass G2 web scraping blocking
    "asp": True,
    # set the poxy location to US
    "country": "US",
}


def parse_search_page(response: ScrapeApiResponse):
    """parse company data from search pages"""
    try:
        selector = response.selector
    except:
        pass
    data = []
    total_results = selector.xpath("//div[@class='ml-half']/text()").get()
    total_results = int(total_results[1:-1]) if total_results else None
    _search_page_size = 20 # each search page contains 20 listings
    total_pages = math.ceil(total_results / _search_page_size)

    for result in selector.xpath("//div[contains(@class, 'paper mb-1')]"):
        name = result.xpath(".//div[contains(@class, 'product-name')]/a/div/text()").get()
        link = result.xpath(".//div[contains(@class, 'product-name')]/a/@href").get()
        image = result.xpath(".//a[contains(@class, 'listing__img')]/img/@data-deferred-image-src").get()
        rate = result.xpath(".//a[contains(@title, 'Reviews')]/div/span[2]/span[1]/text()").get()
        reviews_number = result.xpath(".//a[contains(@title, 'Reviews')]/div/span[1]/text()").get()
        description = result.xpath(".//span[contains(@class, 'paragraph')]/text()").get()
        categories = []
        for category in result.xpath(".//div[span[contains(text(),'Categories')]]/a/text()"):
            categories.append(category.get())
        data.append({
            "name": name,
            "link": link,
            "image": image,
            "rate": float(rate) if rate else None,
            "reviewsNumber": int(reviews_number.replace("(", "").replace(")", "")) if reviews_number else None,
            "description": description,
            "categories": categories
        })

    return {
        "search_data": data,
        "total_pages": total_pages
    }


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
        log.debug(f"{len(remaining_urls)} requests are blocked, trying again with render_js enabled and residential proxies")        
        try:
            failed_requests = [ScrapeConfig(url, **BASE_CONFIG, render_js=True, proxy_pool="public_residential_pool") for url in remaining_urls]
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
    try:
        selector = response.selector
    except:
        pass
    total_reviews = selector.xpath("//li/a[contains(text(),'reviews')]/text()").get()
    total_reviews = int(total_reviews.split()[0]) if total_reviews else None
    _review_page_size = 25 # each review page contains 25 reviews
    total_pages = math.ceil(total_reviews / _review_page_size)    

    data = []
    for review in selector.xpath("//div[@itemprop='review']"):
        author = review.xpath(".//span[@itemprop='author']/meta/@content").get()
        author_profile = review.xpath(".//span[@itemprop='author']/meta[2]/@content").get()
        author_position = review.xpath(".//div[@class='mt-4th']/text()").get()
        author_company_size = review.xpath(".//div[span[contains(text(),'Business')]]/span/text()").getall()
        review_tags = []
        review_tags.extend(review.xpath(".//div[contains(@class, 'tags')]/div/div/text()").getall())
        review_tags.extend(review.xpath(".//div[contains(@class, 'tags')]/div/text()").getall())
        review_date = review.xpath(".//meta[@itemprop='datePublished']/@content").get()
        review_rate = review.xpath(".//div[contains(@class, 'stars')]").get()
        review_title = review.xpath(".//div[@itemprop='name']/text()").get()
        review_likes = "".join(review.xpath(".//div[@itemprop='reviewBody']/div/div/p/text()").getall())
        review_dislikes = "".join(review.xpath(".//div[@itemprop='reviewBody']/div[2]/div/p/text()").getall())
        data.append({
            "author": {
                "authorName": author,
                "authorProfile": author_profile,
                "authorPosition": author_position,
                "authorCompanySize": author_company_size,
            },
            "review": {
                "reviewTags": review_tags,
                "reviewData": review_date,
                "reviewRate": float(review_rate.split("stars-")[-1].split('">')[0]) / 2 if review_rate else None,
                "reviewTitle": review_title.replace('"', '') if review_title else None,
                "reviewLikes": review_likes,
                "reviewDilikes": review_dislikes,
            }})
        
    return {
        "total_pages": total_pages,
        "reviews_data": data
    }


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
        log.debug(f"{len(remaining_urls)} requests are blocked, trying again with render_js enabled and residential proxies")        
        try:
            failed_requests = [ScrapeConfig(url, **BASE_CONFIG, render_js=True, proxy_pool="public_residential_pool") for url in remaining_urls]
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
        if sponsored: # ignore sponsored cards
            continue
        name = alt.xpath(".//div[@itemprop='name']/text()").get()
        link = alt.xpath(".//h3/a[contains(@class, 'link')]/@href").get()
        ranking = alt.xpath(".//div[@class='product-listing__number']/text()").get()
        number_of_reviews = alt.xpath(".//div[div[contains(@class,'stars')]]/span/text()").get() # clean this
        rate = alt.xpath(".//div[div[contains(@class,'stars')]]/span/span/text()").get()
        description = alt.xpath(".//div[@data-max-height-expand-type]/p/text()").get()
        data.append({
            "name": name,
            "link": link,
            "ranking": ranking,
            "numberOfReviews": int(number_of_reviews[1:-1].replace(",", "")) if number_of_reviews else None,
            "rate": float(rate.strip()) if rate else None,
            "description": description
        })
    return data


async def scrape_alternatives(
        product: str, alternatives: Literal["small-business", "mid-market", "enterprise"] = ""
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
            response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG, render_js=True, proxy_pool="public_residential_pool"))
            data = parse_alternatives(response)
        except:
            return
    log.success(f"scraped {len(data)} company alternatives from G2 alternative pages")
    return data
