"""
This is an example web scraper for Linkedin.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
import jmespath
from typing import Dict, List
from urllib.parse import urlencode, quote_plus
from parsel import Selector
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass linkedin.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
    "headers": {
        "Accept-Language": "en-US,en;q=0.5"
    },
    "render_js": True,
    "proxy_pool": "public_residential_pool"    
}

def refine_profile(data: Dict) -> Dict: 
    """refine and clean the parsed profile data"""
    parsed_data = {}
    profile_data = [key for key in data["@graph"] if key["@type"]=="Person"][0]
    profile_data["worksFor"] = [profile_data["worksFor"][0]]
    articles = [key for key in data["@graph"] if key["@type"]=="Article"]
    parsed_data["profile"] = profile_data
    parsed_data["posts"] = articles
    return parsed_data


def parse_profile(response: ScrapeApiResponse) -> Dict:
    """parse profile data from hidden script tags"""
    selector = response.selector
    data = json.loads(selector.xpath("//script[@type='application/ld+json']/text()").get())
    refined_data = refine_profile(data)
    return refined_data


async def scrape_profile(urls: List[str]) -> List[Dict]:
    """scrape public linkedin profile pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    data = []
    # scrape the URLs concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            profile_data = parse_profile(response)
            data.append(profile_data)
        except Exception as e:
            log.error("An occured while scraping profile pages", e)
            pass
    log.success(f"scraped {len(data)} profiles from Linkedin")
    return data


def strip_text(text):
    """remove extra spaces while handling None values"""
    return text.strip() if text != None else text


def parse_company_life(response: ScrapeApiResponse) -> Dict:
    """parse company life page"""
    selector = response.selector
    leaders = []
    for element in selector.xpath("//section[@data-test-id='leaders-at']/div/ul/li"):
        leaders.append({
            "name": element.xpath(".//a/div/h3/text()").get().strip(),
            "title": element.xpath(".//a/div/h4/text()").get().strip(),
            "linkedinProfileLink": element.xpath(".//a/@href").get()
        })
    affiliated_pages = []
    for element in selector.xpath("//section[@data-test-id='affiliated-pages']/div/div/ul/li"):
        affiliated_pages.append({
            "name": element.xpath(".//a/div/h3/text()").get().strip(),
            "industry": strip_text(element.xpath(".//a/div/p[1]/text()").get()),
            "address": strip_text(element.xpath(".//a/div/p[2]/text()").get()),
            "linkeinUrl": element.xpath(".//a/@href").get().split("?")[0]
        })
    similar_pages = []
    for element in selector.xpath("//section[@data-test-id='similar-pages']/div/div/ul/li"):
        similar_pages.append({
            "name": element.xpath(".//a/div/h3/text()").get().strip(),
            "industry": strip_text(element.xpath(".//a/div/p[1]/text()").get()),
            "address": strip_text(element.xpath(".//a/div/p[2]/text()").get()),
            "linkeinUrl": element.xpath(".//a/@href").get().split("?")[0]
        })    
    company_life = {}
    company_life["leaders"] = leaders
    company_life["affiliatedPages"] = affiliated_pages
    company_life["similarPages"] = similar_pages
    return company_life


def parse_company_overview(response: ScrapeApiResponse) -> Dict:
    """parse company main overview page"""
    selector = response.selector
    _script_data = json.loads(selector.xpath("//script[@type='application/ld+json']/text()").get())
    _company_types = [item for item in _script_data['@graph'] if item['@type'] == 'Organization']
    microdata = jmespath.search(
        """{
        name: name,
        url: url,
        mainAddress: address,
        description: description,
        numberOfEmployees: numberOfEmployees.value,
        logo: logo
        }""",
        _company_types[0],
    )
    company_about = {}
    for element in selector.xpath("//div[contains(@data-test-id, 'about-us')]"):
        name = element.xpath(".//dt/text()").get().strip()
        value = element.xpath(".//dd/text()").get().strip()
        if not value:
            value = ' '.join(element.xpath(".//dd//text()").getall()).strip().split('\n')[0]
        company_about[name] = value
    company_overview = {**microdata, **company_about}
    return company_overview


async def scrape_company(urls: List[str]) -> List[Dict]:
    """scrape prublic linkedin company pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    data = []
    # scrape main company URLs then then the life page
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            # create the life page URL from the overiew page response
            company_id = str(response.context["url"]).split("/")[-1]
            company_life_url = f"https://linkedin.com/company/{company_id}/life"
            # request the company life page
            life_page_response = await SCRAPFLY.async_scrape(ScrapeConfig(company_life_url, **BASE_CONFIG))
            overview = parse_company_overview(response)
            life = parse_company_life(life_page_response)
            data.append({"overview": overview, "life": life})
        except Exception as e:
            log.error("An occured while scraping company pages", e)
            pass

    log.success(f"scraped {len(data)} companies from Linkedin")
    return data


def parse_job_search(response: ScrapeApiResponse) -> List[Dict]:
    """parse job data from job search pages"""
    selector = response.selector
    total_results = selector.xpath("//span[contains(@class, 'job-count')]/text()").get()
    total_results = int(total_results.replace(",", "").replace("+", "")) if total_results else None
    data = []
    search_elements = selector.xpath("//section[contains(@class, 'results-list')]/ul/li")
    if len(search_elements) == 0: # pagination pages have a different structure
        search_elements = selector.xpath("//li")

    for element in search_elements:
        data.append({
            "title": element.xpath(".//div/a/span/text()").get().strip(),
            "company": element.xpath(".//div/div[contains(@class, 'info')]/h4/a/text()").get().strip(),
            "address": element.xpath(".//div/div[contains(@class, 'info')]/div/span/text()").get().strip(),
            "timeAdded": element.xpath(".//div/div[contains(@class, 'info')]/div/time/@datetime").get(),
            "jobUrl": element.xpath(".//div/a/@href").get().split("?")[0],
            "companyUrl": element.xpath(".//div/div[contains(@class, 'info')]/h4/a/@href").get().split("?")[0],
        })
    return {"data": data, "total_results": total_results}


async def scrape_job_search(keyword: str, location: str, max_pages: int = None) -> List[Dict]:
    """scrape Linkedin job search"""

    def form_urls_params(keyword, location):
        """form the job search URL params"""
        params = {
            "keywords": quote_plus(keyword),
            "location": location,
        }
        return urlencode(params)

    first_page_url = "https://www.linkedin.com/jobs/search?" + form_urls_params(keyword, location)
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(first_page_url, **BASE_CONFIG))
    data = parse_job_search(first_page)["data"]
    total_results = parse_job_search(first_page)["total_results"]
    # get the total number of pages to scrape, each page contain 25 results
    if max_pages and max_pages * 25 < total_results:
        total_results = max_pages * 25
    
    log.info(f"scraped the first job page, {total_results // 25 - 1} more pages")
    # scrape the remaining pages concurrently
    other_pages_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"
    to_scrape = [
        ScrapeConfig(other_pages_url + form_urls_params(keyword, location) + f"&start={index}", **BASE_CONFIG)
        for index in range(25, total_results + 25, 25)
    ]
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            page_data = parse_job_search(response)["data"]
            data.extend(page_data)
        except Exception as e:
            log.error("An occured while scraping search pagination", e)
            pass

    log.success(f"scraped {len(data)} jobs from Linkedin job search")
    return data


def parse_job_page(response: ScrapeApiResponse):
    """parse individual job data from Linkedin job pages"""
    selector = response.selector
    script_data = json.loads(selector.xpath("//script[@type='application/ld+json']/text()").get())
    description = []
    for element in selector.xpath("//div[contains(@class, 'show-more')]/ul/li/text()").getall():
        text = element.replace("\n", "").strip()
        if len(text) != 0:
            description.append(text)
    script_data["jobDescription"] = description
    script_data.pop("description") # remove the key with the encoded HTML
    return script_data


async def scrape_jobs(urls: List[str]) -> List[Dict]:
    """scrape Linkedin job pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    data = []
    # scrape the URLs concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            data.append(parse_job_page(response))
        except:
            log.debug(f"Job page with {response.context['url']} URL is expired")
    log.success(f"scraped {len(data)} jobs from Linkedin")
    return data


def parse_article_page(response: ScrapeApiResponse) -> Dict:
    """parse individual article data from Linkedin article pages"""
    selector = response.selector
    script_data = json.loads(selector.xpath("//script[@type='application/ld+json']/text()").get())
    script_data["articleBody"] = "".join(selector.xpath("//article/div[@data-test-id='article-content-blocks']/div/p/span/text()").getall())
    return script_data


async def scrape_articles(urls: List[str]) -> List[Dict]:
    """scrape Linkedin articles"""
    to_scrape = [ScrapeConfig(url, asp=True, country="us") for url in urls]
    data = []
    # scrape the URLs concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            data.append(parse_article_page(response))
        except Exception as e:
            log.error("An error occured while scraping article pages", e)
            pass
    log.success(f"scraped {len(data)} articles from Linkedin")
    return data
