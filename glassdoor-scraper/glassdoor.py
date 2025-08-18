"""
This is an example web scraper for Glassdoor.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-glassdoor/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
from enum import Enum
import json
import os
import re
from typing import Dict, List, Optional, Tuple, TypedDict
from urllib.parse import urljoin

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Glassdoor.com requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "country": "GB",
    "render_js": True,
}


def find_hidden_data(result: ScrapeApiResponse) -> Optional[dict]:
    """
    Extract hidden web cache (Apollo Graphql framework) from Glassdoor page HTML
    It's either in NEXT_DATA script or direct apolloState js variable
    """
    # data can be in __NEXT_DATA__ cache
    data = result.selector.css("script#__NEXT_DATA__::text").get()
    if data:
        data = json.loads(data)["props"]["pageProps"]["apolloCache"]
    else:
        match = re.search(r'apolloState":\s*({.+})};', result.content)
        if match:
            data = json.loads(match.group(1))
        else:
            log.warning(f"Could not find __NEXT_DATA__ or apolloState on page {result.context['url']}")
            return None

    def _unpack_apollo_data(apollo_data):
        """
        Glassdoor uses Apollo GraphQL client and the dataset is a graph of references.
        This function unpacks the __ref references to actual values.
        """

        def resolve_refs(data, root):
            if isinstance(data, dict):
                if "__ref" in data:
                    return resolve_refs(root[data["__ref"]], root)
                else:
                    return {k: resolve_refs(v, root) for k, v in data.items()}
            elif isinstance(data, list):
                return [resolve_refs(i, root) for i in data]
            else:
                return data

        if not apollo_data:
            return {}
        return resolve_refs(apollo_data.get("ROOT_QUERY") or apollo_data, apollo_data)

    return _unpack_apollo_data(data)


def parse_jobs(result: ScrapeApiResponse) -> Tuple[List[Dict], List[str]]:
    """Parse Glassdoor jobs page for job data and other page pagination urls"""
    cache = find_hidden_data(result)
    job_cache = next(v for k, v in cache.items() if k.startswith("jobListings"))
    jobs = [v["jobview"]["header"] for v in job_cache["jobListings"]]
    other_pages = [
        urljoin(result.context["url"], page["urlLink"])
        for page in job_cache["paginationLinks"]
        if page["isCurrentPage"] is False
    ]
    return jobs, other_pages


async def scrape_jobs(url: str, max_pages: Optional[int] = None) -> List[Dict]:
    """Scrape Glassdoor job listing page for job listings (with pagination)"""
    log.info("scraping job listings from {}", url)
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))

    jobs, other_page_urls = parse_jobs(first_page)
    _total_pages = len(other_page_urls) + 1
    if max_pages and _total_pages > max_pages:
        other_page_urls = other_page_urls[:max_pages]

    log.info("scraped first page of jobs of {}, scraping remaining {} pages", url, _total_pages - 1)
    other_pages = [ScrapeConfig(url, **BASE_CONFIG) for url in other_page_urls]
    async for result in SCRAPFLY.concurrent_scrape(other_pages):
        if not isinstance(result, ScrapflyScrapeError):
            jobs.extend(parse_jobs(result)[0])
        else:
            log.error(f"failed to scrape {result.api_response.config['url']}, got: {result.message}")
    log.info("scraped {} jobs from {} in {} pages", len(jobs), url, _total_pages)
    return jobs


def parse_reviews(result: ScrapeApiResponse) -> Dict:
    """parse Glassdoor reviews page for review data"""
    cache = find_hidden_data(result)
    if not cache:
        return {}
    reviews_data = next((v for k, v in cache.items() if k.startswith("employerReviewsRG")), {})
    return reviews_data


async def scrape_reviews(url: str, max_pages: Optional[int] = None) -> Dict:
    """Scrape Glassdoor reviews listings from reviews page (with pagination)"""
    log.info("scraping reviews from {}", url)
    first_page_config = ScrapeConfig(url=url, **BASE_CONFIG, timeout=60000, retry=False)
    first_page = await SCRAPFLY.async_scrape(first_page_config)
    if isinstance(first_page, ScrapflyScrapeError):
        log.error(f"Failed to scrape the first page {url}, got: {first_page.message}")
        return {"reviews": [], "message": "Failed to scrape initial page"}

    reviews = parse_reviews(first_page)
    if not reviews or not reviews.get("reviews"):
        log.warning("Could not find review data on page {}. Returning empty results.", url)
        return {"reviews": [], "message": "No data found"}

    total_pages = reviews.get("numberOfPages", 1)
    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    log.info("scraped first page of reviews of {}, scraping remaining {} pages", url, total_pages - 1)
    other_pages = [
        ScrapeConfig(url=Url.change_page(first_page.context["url"], page=page), **BASE_CONFIG)
        for page in range(2, total_pages + 1)
    ]
    async for result in SCRAPFLY.concurrent_scrape(other_pages):
        if not isinstance(result, ScrapflyScrapeError):
            parsed_page = parse_reviews(result)
            if parsed_page and parsed_page.get("reviews"):
                reviews["reviews"].extend(parsed_page["reviews"])
        else:
            if result.api_response:
                log.error(f"failed to scrape {result.api_response.config['url']}, got: {result.message}")
            else:
                log.error(f"An unknown scraping error occurred: {result.message}")
    log.info("scraped {} reviews from {} in {} pages", len(reviews["reviews"]), url, total_pages)
    return reviews


def parse_salaries(result: ScrapeApiResponse) -> Dict:
    """Parse Glassdoor salaries page for salary data"""
    cache = find_hidden_data(result)
    salaries = next(v for k, v in cache.items() if k.startswith("aggregatedSalaryEstimates") and v.get("results"))
    return salaries


async def scrape_salaries(url: str, max_pages: Optional[int] = None) -> Dict:
    """Scrape Glassdoor Salary page for salary listing data (with pagination)"""
    log.info("scraping salaries from {}", url)
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url=url, **BASE_CONFIG))
    salaries = parse_salaries(first_page)
    total_pages = salaries["numPages"]
    if max_pages and total_pages > max_pages:
        total_pages = max_pages

    log.info("scraped first page of salaries of {}, scraping remaining {} pages", url, total_pages - 1)
    other_pages = [
        ScrapeConfig(url=Url.change_page(first_page.context["url"], page=page), **BASE_CONFIG)
        for page in range(2, total_pages + 1)
    ]
    async for result in SCRAPFLY.concurrent_scrape(other_pages):
        if not isinstance(result, ScrapflyScrapeError):
            salaries["results"].extend(parse_salaries(result)["results"])
        else:
            log.error(f"failed to scrape {result.api_response.config['url']}, got: {result.message}")
    log.info("scraped {} salaries from {} in {} pages", len(salaries["results"]), url, total_pages)
    return salaries


class FoundCompany(TypedDict):
    """type hint for company search result"""

    name: str
    id: int
    logoURL: str
    employerId: int
    employerName: str


async def find_companies(query: str) -> List[FoundCompany]:
    """find company Glassdoor ID and name by query. e.g. "ebay" will return "eBay" with ID 7853"""
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=f"https://www.glassdoor.com/api-web/employer/find.htm?autocomplete=true&maxEmployersForAutocomplete=50&term={query}",
            **BASE_CONFIG,
        )
    )
    data = json.loads(result.content)
    companies = []
    for result in data:
        companies.append(
            {
                "name": result["label"],
                "id": result["id"],
                "logoURL": result["logoURL"],
                "employerId": (
                    result["parentRelationshipVO"]["employerId"] if result["parentRelationshipVO"] is not None else None
                ),
                "employerName": (
                    result["parentRelationshipVO"]["employerName"]
                    if result["parentRelationshipVO"] is not None
                    else None
                ),
            }
        )
    return companies


class Region(Enum):
    """glassdoor.com region codes"""

    UNITED_STATES = "1"
    UNITED_KINGDOM = "2"
    CANADA_ENGLISH = "3"
    INDIA = "4"
    AUSTRALIA = "5"
    FRANCE = "6"
    GERMANY = "7"
    SPAIN = "8"
    BRAZIL = "9"
    NETHERLANDS = "10"
    AUSTRIA = "11"
    MEXICO = "12"
    ARGENTINA = "13"
    BELGIUM_NEDERLANDS = "14"
    BELGIUM_FRENCH = "15"
    SWITZERLAND_GERMAN = "16"
    SWITZERLAND_FRENCH = "17"
    IRELAND = "18"
    CANADA_FRENCH = "19"
    HONG_KONG = "20"
    NEW_ZEALAND = "21"
    SINGAPORE = "22"
    ITALY = "23"


class Url:
    """
    Helper URL generator that generates full URLs for glassdoor.com pages
    from given employer name and ID
    For example:
    > GlassdoorUrl.overview("eBay Motors Group", "4189745")
    https://www.glassdoor.com/Overview/Working-at-eBay-Motors-Group-EI_IE4189745.11,28.htm

    Note that URL formatting is important when it comes to scraping Glassdoor
    as unusual URL formats can lead to scraper blocking.
    """

    @staticmethod
    def overview(employer: str, employer_id: str, region: Optional[Region] = None) -> str:
        employer = employer.replace(" ", "-")
        url = f"https://www.glassdoor.com/Overview/Working-at-{employer}-EI_IE{employer_id}"
        # glassdoor is allowing any prefix for employer name and
        # to indicate the prefix suffix numbers are used like:
        # https://www.glassdoor.com/Overview/Working-at-eBay-Motors-Group-EI_IE4189745.11,28.htm
        # 11,28 is the slice where employer name is
        _start = url.split("/Overview/")[1].find(employer)
        _end = _start + len(employer)
        url += f".{_start},{_end}.htm"
        if region:
            return url + f"?filter.countryId={region.value}"
        return url

    @staticmethod
    def reviews(employer: str, employer_id: str, region: Optional[Region] = None) -> str:
        employer = employer.replace(" ", "-")
        url = f"https://www.glassdoor.com/Reviews/{employer}-Reviews-E{employer_id}.htm?"
        if region:
            return url + f"?filter.countryId={region.value}"
        return url

    @staticmethod
    def salaries(employer: str, employer_id: str, region: Optional[Region] = None) -> str:
        employer = employer.replace(" ", "-")
        url = f"https://www.glassdoor.com/Salary/{employer}-Salaries-E{employer_id}.htm?"
        if region:
            return url + f"?filter.countryId={region.value}"
        return url

    @staticmethod
    def jobs(employer: str, employer_id: str, region: Optional[Region] = None) -> str:
        employer = employer.replace(" ", "-")
        url = f"https://www.glassdoor.com/Jobs/{employer}-Jobs-E{employer_id}.htm?"
        if region:
            return url + f"?filter.countryId={region.value}"
        return url

    @staticmethod
    def change_page(url: str, page: int) -> str:
        """update page number in a glassdoor url"""
        if re.search(r"_P\d+\.htm", url):
            new = re.sub(r"(?:_P\d+)*.htm", f"_P{page}.htm", url)
        else:
            new = re.sub(".htm", f"_P{page}.htm", url)
        assert new != url
        return new
