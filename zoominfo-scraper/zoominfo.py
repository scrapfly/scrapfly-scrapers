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
    # set the proxy country to US
    "country": "US",
}


def parse_company(response: ScrapeApiResponse) -> List[Dict]:
    """parse zoominfo company page for company data"""
    selector = response.selector
    data = selector.css("script#ng-state::text").get()
    data = json.loads(data)["pageData"]
    return data


def parse_directory(response: ScrapeApiResponse) -> dict:
    """parse zoominfo directory pages"""
    selector = response.selector
    companies = selector.css("a.company-name.link::attr(href)").getall()
    pagination = selector.css("a.page-link::attr(href)").getall()
    return {"companies": companies, "pagination": pagination}


async def scrape_comapnies(urls: List[str]) -> List[Dict]:
    """scrape company data from zoominfo company pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    companies = []
    failed = []
    try:
        async for response in SCRAPFLY.concurrent_scrape(to_scrape):
            companies.append(parse_company(response))
    except ScrapflyAspError:
            failed.append(response.context['url'])
    if len(failed) != 0:
        log.debug(f"{len(failed)} requests are blocked, trying again with render_js enabled and residential proxies")
        for url in failed:
            try:
                response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG, render_js=True, proxy_pool="public_residential_pool"))
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
        faqs.append({
            "question": question.strip() if question else None,
            "answer": answer
        })
    return faqs


async def scrape_faqs(url: str) -> List[Dict]:
    """scrape faqs from Zoominfo company pages"""       
    response = await SCRAPFLY.async_scrape(ScrapeConfig(
        url=url, **BASE_CONFIG, render_js=True, auto_scroll=True, wait_for_selector="div.faqs"
    ))
    faqs = parse_faqs(response)
    log.success(f"scraped {len(faqs)} FAQs from company page")
    return faqs