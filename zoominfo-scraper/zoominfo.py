"""
This is an example web scraper for zoominfo.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
from typing import Dict, List
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse, ScrapflyAspError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass zoominfo.com web scraping blocking
    "asp": True,
    # set the proxy country to CA
    "country": "CA",
}


def parse_company(response: ScrapeApiResponse) -> List[Dict]:
    """parse zoominfo company page for company data"""
    selector = response.selector
    data = selector.css("script#ng-state::text").get()
    data = json.loads(data)["pageData"]
    return data

def parse_directory(response: ScrapeApiResponse) -> dict:
    """parse zoominfo directory pages"""
    data = response.selector.css("script#ng-state::text").get()
    data = json.loads(data)    
    # Check which data source is available
    companies_search_data = data.get("companiesSearchData")
    ai_search_results = data.get("aiSearchResults")
    
    if companies_search_data:
        # Use companiesSearchData logic
        companies_data = companies_search_data.get("companies", [])
        companies = [company.get("companyUrl") for company in companies_data]
        pagination_data = companies_search_data.get("paginationData", {}).get("pages", [])
        pagination = [page.get("url") for page in pagination_data if page.get("url")]
    elif ai_search_results:
        # Use aiSearchResults logic
        companies_data = ai_search_results.get("data", [])
        companies = [company.get("companyUrl") for company in companies_data if company.get("companyUrl")]
        # For aiSearchResults, derive pagination from metadata
        total_results = ai_search_results.get("totalResults", 0)
        page_num = data.get("pageNum", 1)
        base_url = data.get("baseUrl", "")
        # Calculate pagination (assuming results per page based on current data length)
        results_per_page = len(companies_data) if companies_data else 10
        if results_per_page > 0 and total_results > 0:
            total_pages = (total_results + results_per_page - 1) // results_per_page
            pagination = [f"{base_url}?pageNum={i}" for i in range(1, total_pages + 1)]
        else:
            pagination = []
    else:
        # Neither data source available
        companies = []
        pagination = []
    
    return {"companies": companies, "pagination": pagination}

async def scrape_comapnies(urls: List[str]) -> List[Dict]:
    """scrape company data from zoominfo company pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    companies = []
    failed = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        # Check if this is a successful response or an error
        if isinstance(response, ScrapeApiResponse):
            try:
                companies.append(parse_company(response))
            except Exception as e:
                log.error(f"Failed to parse company data: {e}")
                failed.append(response.context["url"])
        else:
            # This is an error response (ApiHttpServerError, ScrapflyAspError, etc.)
            log.warning(f"Request failed with error: {response}")
            # Extract URL from the response context if available
            if hasattr(response, 'context') and 'url' in response.context:
                failed.append(response.context["url"])

    if len(failed) != 0:
        log.debug(f"{len(failed)} requests are blocked, trying again with render_js enabled and residential proxies")
        for url in failed:
            try:
                response = await SCRAPFLY.async_scrape(
                    ScrapeConfig(url, **BASE_CONFIG, render_js=True, proxy_pool="public_residential_pool")
                )
                companies.append(parse_company(response))
            except ScrapflyAspError:
                pass
    log.success(f"scraped {len(companies)} company pages data")
    return companies


async def scrape_directory(url: str, scrape_pagination=True) -> List[str]:
    """scrape zoominfo directory pages for company page URLs"""
    # parse first page of the results
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_directory(response)
    companies = data["companies"]
    pagination = data["pagination"]
    # parse other pages of the results
    if scrape_pagination:
        for page_url in pagination:
            companies.extend(await scrape_directory("https://www.zoominfo.com" + page_url, scrape_pagination=False))
    log.success(f"scraped {len(companies)} company page URLs from directory pages")
    return companies


def parse_faqs(response: ScrapeApiResponse) -> List[Dict]:
    """parse faqs from Zoominfo company pages"""
    selector = response.selector
    faqs = []
    for faq in selector.xpath("//div[@class='faqs']/zi-directories-faqs-item"):
        question = faq.css("span.question::text").get()
        answer = faq.css("span.answer::text").get()
        if not answer:
            answer = faq.css("span.answer > p::text").get()
        faqs.append({"question": question.strip() if question else None, "answer": answer})
    return faqs


async def scrape_faqs(url: str) -> List[Dict]:
    """scrape faqs from Zoominfo company pages"""
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(url=url, **BASE_CONFIG, render_js=True, auto_scroll=True, wait_for_selector="div.faqs")
    )
    faqs = parse_faqs(response)
    log.success(f"scraped {len(faqs)} FAQs from company page")
    return faqs
