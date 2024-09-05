"""
This is an example web scraper for wellfound.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
from typing import Dict, List, TypedDict
from copy import deepcopy
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass wellfound.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
}


class JobData(TypedDict):
    """type hint for scraped job result data"""
    id: str
    title: str
    slug: str
    remtoe: bool
    primaryRoleTitle: str
    locationNames: Dict
    liveStartAt: int
    jobType: str
    description: str
    # there are more fields, but these are basic ones


class CompanyData(TypedDict):
    """type hint for scraped company result data"""
    id: str
    badges: list
    companySize: str
    highConcept: str
    highlightedJobListings: List[JobData]
    logoUrl: str
    name: str
    slug: str
    # there are more fields, but these are basic ones


def extract_apollo_state(result: ScrapeApiResponse):
    """extract apollo state graph from a page"""
    data = result.selector.css("script#__NEXT_DATA__::text").get()
    if data == None:
        return
    data = json.loads(data)
    graph = data["props"]["pageProps"]["apolloState"]["data"]
    return graph


def unpack_node_references(node, graph, debug=False):
    """
    unpacks references in a graph node to a flat node structure:
    >>> unpack_node_references({"field": {"id": "reference1", "type": "id"}}, graph={"reference1": {"foo": "bar"}})
    {'field': {'foo': 'bar'}}
    """
    def flatten(value):
        try:
            if value["type"] != "id":
                return value
        except (KeyError, TypeError):
            return value
        data = deepcopy(graph[value["id"]])
        # flatten nodes too:
        if data.get("node"):
            data = flatten(data["node"])
        if debug:
            data["__reference"] = value["id"]
        return data

    node = flatten(node)

    for key, value in node.items():
        if isinstance(value, list):
            node[key] = [flatten(v) for v in value]
        elif isinstance(value, dict):
            node[key] = unpack_node_references(value, graph)
    return node


def parse_company(result: ScrapeApiResponse) -> CompanyData:
    """parse company data from wellfound.com company page"""
    graph = extract_apollo_state(result)
    company = None
    for key in graph:
        if key.startswith("Startup:"):
            company = graph[key]
            break
    else:
        raise ValueError("no embedded company data could be found")
    return unpack_node_references(company, graph)


async def retry_failure(url: str, _retries: int = 0):
    """retry failed requests with a maximum number of retries"""
    max_retries = 3
    try:
        response = await SCRAPFLY.async_scrape(
            ScrapeConfig(url, **BASE_CONFIG, render_js=True, proxy_pool="public_residential_pool")
        )
        if response.status_code == 403:
            if _retries < max_retries:
                log.debug("Retrying failed request")
                return await retry_failure(url, _retries=_retries + 1)
            else:
                raise Exception("Unable to scrape rge first search page, max retries exceeded")
        return response
    except Exception as e:
        if _retries < max_retries:
            log.debug("Retrying failed request")
            return await retry_failure(url, _retries=_retries + 1)
        else:
            raise Exception("Unable to scrape rge first search page, max retries exceeded")


async def scrape_search(role: str = "", location: str = "", max_pages: int = None) -> List[CompanyData]:
    """scrape wellfound.com search"""
    # wellfound.com has 3 types of search urls: for roles, for locations and for combination of both
    if role and location:
        url = f"https://wellfound.com/role/l/{role}/{location}"
    elif role:
        url = f"https://wellfound.com/role/{role}"
    elif location:
        url = f"https://wellfound.com/location/{location}"
    else:
        raise ValueError("need to pass either role or location argument to scrape search")
    companies = []
    log.info(f"scraping first page of search, {role} in {location}")
    first_page = await retry_failure(url)
    graph = extract_apollo_state(first_page)
    companies.extend([unpack_node_references(graph[key], graph) for key in graph if key.startswith("StartupResult")])
    seo_landing_key = next(key for key in graph["ROOT_QUERY"]["talent"] if "seoLandingPageJobSearchResults" in key)
    total_pages = graph["ROOT_QUERY"]["talent"][seo_landing_key]["pageCount"]
    # find total page count
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    # next, scrape the remaining search pages directly from the API
    log.info(f"scraping search pagination, remaining ({total_pages - 1}) more pages")    
    other_pages = [ScrapeConfig(url + f"?page={page}", **BASE_CONFIG) for page in range(2, total_pages + 1)]
    async for response in SCRAPFLY.concurrent_scrape(other_pages):
        try:
            graph = extract_apollo_state(response)
            companies.extend([unpack_node_references(graph[key], graph) for key in graph if key.startswith("StartupResult")])
        except Exception as e:
            log.debug(f"Error occured while crawling search: {e}")
            pass
    log.success(f"scraped {len(companies)} job listings from search pages")        
    return companies


async def scrape_companies(urls: List[str]) -> List[CompanyData]:
    """scrape wellfound.com companies"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    companies = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            companies.append(parse_company(response))
        except:
            pass
    log.success(f"scraped {len(companies)} comapny listings data from company pages")         
    return companies
