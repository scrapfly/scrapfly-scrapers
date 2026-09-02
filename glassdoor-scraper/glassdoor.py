"""
This is an example web scraper for Glassdoor.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-glassdoor/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
from enum import Enum
import json
import math
import os
import re
from typing import Dict, List, Optional, Tuple, TypedDict
from urllib.parse import quote_plus, urljoin

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Glassdoor.com requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "country": "US",
    "render_js": True,
}


def parse_jobs(result: ScrapeApiResponse) -> Tuple[List[Dict], List[str]]:
    """Parse Glassdoor jobs page for job data and other page pagination urls"""
    selector = result.selector
    job_data = []
    for box in selector.xpath("//div[contains(@class, 'jobCard JobCard')]"):
        job_data.append({
            "jobTitle": box.xpath(".//a/text()").get(),
            "jobLink": urljoin(result.context["url"], box.xpath(".//a/@href").get()),
            "job_location": box.xpath(".//div[@data-test='emp-location']/text()").get(),
            "jobSalary": box.xpath(".//div[@data-test='detailSalary']/text()").get(),
            "jobDate": box.xpath(".//div[@data-test='job-age']/text()").get(),
        })

    script_data = selector.xpath("//script[contains(text(), 'paginationLinks')]/text()").get()
    match = re.search(r'\\"paginationLinks\\":\s*(\[.*?\])\s*,\s*\\"searchResultsMetadata\\"', script_data or "")
    if not match:
        log.warning("could not find pagination links on {}", result.context["url"])
        return job_data, []
    unescaped = match.group(1).replace('\\"', '"').replace('\\u0026', '&')
    pagination_links = json.loads(unescaped)
    
    other_pages = [
        urljoin(result.context["url"], page["urlLink"])
        for page in pagination_links
        if page["isCurrentPage"] is False
    ]
    
    return job_data, other_pages


async def scrape_jobs(url: str, max_pages: Optional[int] = None) -> List[Dict]:
    """Scrape Glassdoor job listing page for job listings (with pagination)"""
    log.info("scraping job listings from {}", url)
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))

    jobs, other_page_urls = parse_jobs(first_page)
    total_pages = len(other_page_urls) + 1
    # the first page is already scraped, so max_pages caps the remaining pages
    if max_pages and total_pages > max_pages:
        other_page_urls = other_page_urls[: max_pages - 1]

    log.info("scraped first page of jobs of {}, scraping remaining {} pages", url, len(other_page_urls))
    other_pages = [ScrapeConfig(page_url, **BASE_CONFIG) for page_url in other_page_urls]
    async for result in SCRAPFLY.concurrent_scrape(other_pages):
        if not isinstance(result, ScrapflyScrapeError):
            jobs.extend(parse_jobs(result)[0])
        else:
            log.error(f"failed to scrape {result.api_response.config['url']}, got: {result.message}")
    log.info("scraped {} jobs from {} in {} of {} pages", len(jobs), url, len(other_page_urls) + 1, total_pages)
    return jobs


def parse_reviews_api_metadata(result: ScrapeApiResponse) -> Dict:
    """parse Glassdoor reviews api metadata from html page"""
    selector = result.selector
    script_data = selector.xpath("//script[contains(text(), 'profileId')]/text()").get()
    match = re.search(r'"employer"\s*:\s*\{', script_data or "")
    if not match:
        raise ValueError(f"could not find employer metadata on {result.context['url']}")
    # the employer object holds nested objects, so it is decoded instead of matched with a regex
    employer_metadata, _ = json.JSONDecoder().raw_decode(script_data, match.end() - 1)
    return {
        'employer_id': int(employer_metadata['id']),
        'dynamic_profile_id': int(employer_metadata['profileId']),
    }


async def scrape_reviews(url: str, max_pages: Optional[int] = None) -> List[Dict]:
    """Scrape Glassdoor reviews listings from reviews page (with pagination)"""

    # the reviews API no longer returns a page count, so the page size is used to derive it
    page_size = 5

    def generate_api_request_config(employer_id: int, dynamic_profile_id: int, page_number: int) -> ScrapeConfig:
        return ScrapeConfig(
            url='https://www.glassdoor.com/bff/employer-profile-mono/employer-reviews',
            method='POST',
            asp=True,
            country="US",
            headers={
                "content-type": "application/json",
            },
            body=json.dumps({
                "applyDefaultCriteria":True,
                "employerId":employer_id,
                "employmentStatuses":["REGULAR","PART_TIME"],
                "jobTitle":None,
                "goc":None,
                "location":{},
                "defaultLanguage":"eng",
                "language":"eng",
                "mlHighlightSearch":None,
                "onlyCurrentEmployees":False,
                "overallRating":None,
                "pageSize":page_size,"page":page_number,
                "preferredTldId":0,
                "reviewCategories":[],
                "sort":"DATE",
                "textSearch":"",
                "worldwideFilter":False,
                "dynamicProfileId":dynamic_profile_id,
                "useRowProfileTldForRatings":True,
                "enableKeywordSearch":True
            })
        )

    review_data = []
    log.info("scraping reviews api requirements from {}", url)

    first_page_html = await SCRAPFLY.async_scrape(ScrapeConfig(url=url, **BASE_CONFIG))
    employer_metadata = parse_reviews_api_metadata(first_page_html)

    first_api_page = await SCRAPFLY.async_scrape(
        generate_api_request_config(employer_metadata['employer_id'], employer_metadata['dynamic_profile_id'], 1)
    )
    first_page_data = json.loads(first_api_page.content)
    first_page_reviews = first_page_data['data']['employerReviews']
    review_data.extend(first_page_reviews['reviews'])
    # the API dropped the numberOfPages field, the page count comes from the filtered review count
    total_pages = math.ceil(first_page_reviews['filteredReviewsCount'] / page_size)

    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    log.info("scraping reviews pagination from {}, scraping remaining {} pages", url, total_pages - 1)
    remaining_pages = [
        generate_api_request_config(employer_metadata['employer_id'], employer_metadata['dynamic_profile_id'], page)
        for page in range(2, total_pages + 1)
    ]

    async for result in SCRAPFLY.concurrent_scrape(remaining_pages):
        if isinstance(result, ScrapflyScrapeError):
            log.error(f"failed to scrape a reviews API page, got: {result.message}")
            continue
        page_data = json.loads(result.content)
        review_data.extend(page_data['data']['employerReviews']['reviews'])

    log.info("scraped {} reviews from {} in {} pages", len(review_data), url, total_pages)
    return review_data


def parse_salary_range(salary_range: str) -> List[Dict]:
    """parse a glassdoor salary range like "$70.5K - $100K" into min and max percentiles"""
    # an hourly rate is not comparable to an annual salary, so it is not reported as one
    if re.search(r"/\s*h(?:r|our)|hourly|per hour", salary_range, re.I):
        return []
    # the two numbers have to sit around a range separator, otherwise a rating or a
    # submission count rendered in the same node gets read as a salary
    match = re.search(
        r"([\d.,]+)\s*([KkMm])?\s*(?:/\s*\w+)?\s*(?:[-–—]|\bto\b)\s*\$?\s*([\d.,]+)\s*([KkMm])?",
        salary_range,
    )
    if not match:
        return []
    values = []
    for number, suffix in ((match.group(1), match.group(2)), (match.group(3), match.group(4))):
        try:
            value = float(number.replace(",", ""))
        except ValueError:
            return []
        # the magnitude suffix has to be applied arithmetically, replacing "K" with "000" mangles decimals
        values.append(value * {"k": 1_000, "m": 1_000_000}.get((suffix or "").lower(), 1))
    if not 0 < values[0] <= values[1]:
        return []
    return [{"ident": "min", "value": values[0]}, {"ident": "max", "value": values[1]}]


def parse_salaries(result: ScrapeApiResponse) -> Dict:
    """Parse Glassdoor salaries page for salary data"""
    
    salary_data = {
        "results": [],
        "numPages": 1,
        "salaryCount": 0,
        "jobTitleCount": 0
    }
        
    salary_items = result.selector.css('[data-test="salary-item"]')

    for item in salary_items:
        job_title = item.css('[class*="SalaryItem_jobTitle"]::text').get()
        if not job_title:
            continue

        salary_range = " ".join(
            text.strip() for text in item.css('[class*="SalaryItem_salaryRange"] ::text').getall()
        ).strip() or None
        salary_count_text = item.css('[class*="SalaryItem_salaryCount"]::text').get() or ""
        
        salary_count = 0
        if "Salaries submitted" in salary_count_text:
            try:
                salary_count = int(salary_count_text.split()[0].replace(',', ''))
            except (ValueError, IndexError):
                log.warning("could not parse salary count {!r}", salary_count_text)
        
        salary_item = {
            "jobTitle": {
                "text": job_title,
            },
            "salaryCount": salary_count,
            "basePayStatistics": {
                "percentiles": []
            }
        }
        
        percentiles = parse_salary_range(salary_range) if salary_range else []
        if salary_range and not percentiles:
            log.warning("could not parse salary range {!r}", salary_range)
        salary_item["basePayStatistics"]["percentiles"] = percentiles

        salary_data["results"].append(salary_item)
    
    # Extract pagination from HTML
    page_links = result.selector.css('[class*="pagination_PageNumberText"]::text').getall()
    if page_links:
        try:
            salary_data["numPages"] = max(int(page) for page in page_links if page.isdigit())
        except ValueError:
            pass
    
    # Extract job title count from HTML
    result_count_text = result.selector.css('[class*="SortBar_SearchCount"]::text').get() or ""
    if "job titles" in result_count_text:
        try:
            count_str = result_count_text.split()[0]
            salary_data["jobTitleCount"] = int(count_str.replace(',', ''))
        except (ValueError, IndexError):
            pass
    
    salary_data["salaryCount"] = sum(item["salaryCount"] for item in salary_data["results"])
    
    log.info(f"Parsed {len(salary_data['results'])} salary items")
    return salary_data


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
    salaries["salaryCount"] = sum(item["salaryCount"] for item in salaries["results"])
    log.info("scraped {} salaries from {} in {} pages", len(salaries["results"]), url, total_pages)
    return salaries


class FoundCompany(TypedDict):
    """type hint for company search result"""

    name: str
    id: int
    shortName: str
    logoURL: Optional[str]
    websiteURL: Optional[str]


async def find_companies(query: str) -> List[FoundCompany]:
    """find company Glassdoor ID and name by query. e.g. "ebay" will return "eBay" with ID 7853"""
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=f"https://www.glassdoor.com/autocomplete/employers?term={quote_plus(query)}",
            # the autocomplete endpoint answers with json, so there is nothing to render
            asp=True,
            country="US",
        )
    )
    data = json.loads(result.content)
    companies = []
    for company in data:
        companies.append(
            {
                "name": company["label"],
                "id": company["id"],
                "shortName": company.get("shortName", ""),
                "logoURL": company.get("logoURL"),
                "websiteURL": company.get("websiteURL", ""),
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
        url = f"https://www.glassdoor.com/Reviews/{employer}-Reviews-E{employer_id}.htm"
        if region:
            return url + f"?filter.countryId={region.value}"
        return url

    @staticmethod
    def salaries(employer: str, employer_id: str, region: Optional[Region] = None) -> str:
        employer = employer.replace(" ", "-")
        url = f"https://www.glassdoor.com/Salary/{employer}-Salaries-E{employer_id}.htm"
        if region:
            return url + f"?filter.countryId={region.value}"
        return url

    @staticmethod
    def jobs(employer: str, employer_id: str, region: Optional[Region] = None) -> str:
        employer = employer.replace(" ", "-")
        url = f"https://www.glassdoor.com/Jobs/{employer}-Jobs-E{employer_id}.htm"
        if region:
            return url + f"?filter.countryId={region.value}"
        return url

    @staticmethod
    def change_page(url: str, page: int) -> str:
        """update page number in a glassdoor url"""
        if re.search(r"_P\d+\.htm", url):
            new = re.sub(r"(?:_P\d+)*\.htm", f"_P{page}.htm", url, count=1)
        else:
            new = re.sub(r"\.htm", f"_P{page}.htm", url, count=1)
        if new == url:
            raise ValueError(f"cannot add a page number to url: {url}")
        return new
