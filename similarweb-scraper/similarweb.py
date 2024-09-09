"""
This is an example web scraper for SimilarWeb.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import re
import os
import gzip
import json
import jmespath
from parsel import Selector
from typing import Dict, List, Optional
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass bestbuy.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
}

def parse_hidden_data(response: ScrapeApiResponse) -> List[Dict]:
    """parse website insights from hidden script tags"""
    selector = response.selector
    script = selector.xpath("//script[contains(text(), 'window.__APP_DATA__')]/text()").get()
    data = json.loads(re.findall(r"(\{.*?)(?=window\.__APP_META__)", script, re.DOTALL)[0])
    return data


async def scrape_website(domains: List[str]) -> List[Dict]:
    """scrape website inights from website pages"""
    # define a list of similarweb URLs for website pages
    urls = [f"https://www.similarweb.com/website/{domain}/" for domain in domains]
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    data = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        website_data = parse_hidden_data(response)["layout"]["data"]
        data.append(website_data)
    log.success(f"scraped {len(data)} website insights from similarweb website pages")
    return data


def parse_website_compare(response: ScrapeApiResponse, first_domain: str, second_domain: str) -> Dict:
    """parse website comparings inights between two domains"""

    def parse_domain_insights(data: Dict, second_domain: Optional[bool]=None) -> Dict:
        """parse each website data and add it to each domain"""
        data_key = data["layout"]["data"]
        if second_domain:
            data_key = data_key["compareCompetitor"] # the 2nd website compare key is nested
        parsed_data = jmespath.search(
            """{
            overview: overview,
            traffic: traffic,
            trafficSources: trafficSources,
            ranking: ranking,
            demographics: geography
            }""",
            data_key
        )
        return parsed_data

    script_data = parse_hidden_data(response)
    data = {}
    data[first_domain] = parse_domain_insights(data=script_data)
    data[second_domain] = parse_domain_insights(data=script_data, second_domain=True)
    return data


async def scrape_website_compare(first_domain: str, second_domain: str) -> Dict:
    """parse website comparing data from similarweb comparing pages"""
    url = f"https://www.similarweb.com/website/{first_domain}/vs/{second_domain}/"
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_website_compare(response, first_domain, second_domain)
    f"scraped comparing insights between {first_domain} and {second_domain}"
    log.success(f"scraped comparing insights between {first_domain} and {second_domain}")
    return data


def parse_sitemaps(response: ScrapeApiResponse) -> List[str]:
    """parse links for bestbuy sitemap"""
    bytes_data = response.scrape_result['content'].getvalue()
    # decode the .gz file
    xml = bytes_data.decode('utf-8')
    selector = Selector(xml)
    data = []
    for url in selector.xpath("//url/loc/text()"):
        data.append(url.get())
    return data


async def scrape_sitemaps(url: str) -> List[str]:
    """scrape link data from bestbuy sitemap"""
    promo_urls = None
    try:
        response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
        promo_urls = parse_sitemaps(response)
        log.success(f"scraped {len(promo_urls)} urls from sitemaps")
    except:
        log.info("couldnt' scrape sitemaps, request was blocked")
        pass
    return promo_urls


def parse_trending_data(response: ScrapeApiResponse) -> List[Dict]:
    """parse hidden trending JSON data from script tags"""
    selector = response.selector
    json_data = json.loads(selector.xpath("//script[@id='dataset-json-ld']/text()").get())["mainEntity"]
    data = {}
    data["name"] = json_data["name"]
    data["url"] = response.scrape_result["url"]
    data["list"] = json_data["itemListElement"]
    return data


async def scrape_trendings(urls: List[str]) -> List[Dict]:
    """parse trending websites data"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    data = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        category_data = parse_trending_data(response)
        data.append(category_data)
    log.success(f"scraped {len(data)} trneding categories from similarweb")
    return data    