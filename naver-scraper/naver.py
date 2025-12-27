"""
This is an example web scraper for Naver.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-naver/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import json
import re
from pathlib import Path
from urllib.parse import urlencode, urlparse
from loguru import logger as log
from typing import List, Dict, TypedDict, Optional, Literal, Any

from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # Naver.com requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "render_js": True,
}

output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)


# Type definitions
SearchType = Literal["web", "image", "blog", "cafe", "kin", "news", "influencer", "short content", "video"]
SortType = Literal["sim", "date", "asc", "dsc"]
PeriodType = Literal["all", "1d", "1w", "1m", "6m", "1y"]


# URL Builder Functions
def _build_nso_filter(sort: Optional[SortType] = None, period: Optional[PeriodType] = None) -> str:
    """
    Build NSO (Naver Search Options) filter string.

    NSO format: so:{sort},p:{period}
    - so: sort order (dd=date desc, da=date asc, r=relevance)
    - p: period filter (1d, 1w, 1m, 6m, 1y)
    Args:
        sort: Sort type (sim, date, asc, dsc)
        period: Time period filter (all, 1d, 1w, 1m, 6m, 1y)
    Returns:
        NSO filter string
    """
    nso_parts = []
    if sort:
        sort_map = {
            "sim": "r",  # relevance
            "date": "dd",  # date descending (recent first)
            "asc": "da",  # date ascending (oldest first)
            "dsc": "dd",  # date descending (alias)
        }
        nso_parts.append(f"so:{sort_map.get(sort, 'r')}")
    if period:
        nso_parts.append(f"p:{period}")

    return ",".join(nso_parts) if nso_parts else ""


def _build_search_url(
    query: str,
    search_type: SearchType = "web",
    page: int = 1,
    display: int = 10,
    sort: Optional[SortType] = None,
    period: Optional[PeriodType] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> str:
    """
    Build comprehensive Naver search URL with all parameters.

    Args:
        query: Search term (supports Korean UTF-8)
        search_type: Type of search (web, image, blog, cafe, kin, etc.)
        page: Page number (1-indexed)
        display: Results per page (default 10)
        sort: Sort type (sim, date, asc, dsc)
        period: Time period filter (all, 1d, 1w, 1m, 6m, 1y)

    Returns:
        Complete Naver search URL
    """
    base_url = "https://search.naver.com/search.naver"

    # Calculate pagination start parameter
    # Standard formula for most search types: (page - 1) * display + 1
    start = (page - 1) * display + 1

    # Build base parameters
    params = {
        "query": query,
        "start": start,
    }

    # Add search-type specific parameters
    type_configs = {
        "web": {
            "where": "web",
        },
        "image": {
            "where": "image",
            "ssc": "tab.image.all",
        },
        "blog": {
            "where": "blog",
            "ssc": "tab.blog.all",
        },
        "cafe": {
            "where": "cafe",
            "ssc": "tab.cafe.all",
        },
        "kin": {
            "where": "kin",
            "ssc": "tab.kin.kqna",
        },
        "news": {
            "where": "news",
            "ssc": "tab.news.all",
        },
        "influencer": {
            "where": "influencer",
            "ssc": "tab.influencer.all",
        },
        "short content": {
            "ssc": "tab.shortents.all",
        },
        "video": {
            "where": "video",
            "ssc": "tab.video.all",
        },
    }

    # Update params with search type config
    params.update(type_configs.get(search_type, {"where": search_type}))

    # Build and add NSO filter if applicable
    nso = _build_nso_filter(sort, period)
    if nso:
        params["nso"] = nso


    # Build final URL with proper encoding
    query_string = urlencode(params)
    log.info(f"Search URL: {base_url}?{query_string}")
    return f"{base_url}?{query_string}"


# Define data structures with TypedDict


class SearchResult(TypedDict):
    """type hint for scraped search result data"""

    title: str
    url: str
    description: str
    # ... other fields


# Parsing functions
def parse_web_search(result: ScrapeApiResponse) -> Dict[str, Any]:
    """
    Parse web search results from JSON embedded in HTML.

    Args:
        result: ScrapFly API response

    Returns:
        Dictionary containing results and max_pages
    """
    content = result.content
    selector = result.selector
    results = []

    # Extract JSON from entry.bootstrap
    pattern = r"entry\.bootstrap\([^,]+,\s*\{"
    match = re.search(pattern, content)

    if match:
        json_start = content.index("{", match.end() - 1)

        # Extract balanced JSON object
        brace_count = 0
        in_string = False
        escape = False

        for i in range(json_start, len(content)):
            char = content[i]

            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue

            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = content[json_start : i + 1]
                        break

        # Parse JSON and extract results
        try:
            data = json.loads(json_str)
            items = data.get("body", {}).get("props", {}).get("children", [])

            if items and "props" in items[0]:
                for idx, item in enumerate(items[0]["props"].get("children", []), 1):
                    if item.get("templateId") != "webItem":
                        continue

                    props = item.get("props", {})
                    title = props.get("title", "").replace("<mark>", "").replace("</mark>", "")
                    url = props.get("href", "")

                    if not title or not url:
                        continue

                    # Extract source
                    source = None
                    subtexts = props.get("profile", {}).get("subTexts", [])
                    if subtexts:
                        source = subtexts[0].get("text", "") if isinstance(subtexts[0], dict) else str(subtexts[0])
                    source = source
                    # Extract rank
                    click_log = props.get("clickLog", {})
                    rank = click_log.get("title", {}).get("r") or click_log.get("profile", {}).get("r") or idx

                    results.append(
                        {
                            "title": title,
                            "url": url,
                            "snippet": props.get("bodyText", "").replace("<mark>", "").replace("</mark>", ""),
                            "source": source,
                            "rank": rank,
                        }
                    )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.debug(f"JSON parsing error: {e}")

    # Extract max_pages from pagination
    max_pages = None
    page_numbers = []
    for link in selector.css("div.sc_page_inner a.btn"):
        href = link.css("::attr(href)").get("")
        text = link.css("::text").get("")

        page_match = re.search(r"[?&]page=(\d+)", href)
        if page_match:
            page_numbers.append(int(page_match.group(1)))
        elif text and text.strip().isdigit():
            page_numbers.append(int(text.strip()))

    if page_numbers:
        max_pages = max(page_numbers)
    num_of_displayed_results = len(results)
    log.info(f"Number of displayed results: {num_of_displayed_results}")
    return {"results": results, "max_pages": max_pages, "num_of_displayed_results": num_of_displayed_results}


# Scraping functions


async def scrape_web_search(
    query: str,
    max_pages: int = 3,
    sort: Optional[SortType] = None,
    period: Optional[PeriodType] = None,
    scrape_all_pages: bool = False,
) -> {}:
    """
    Scrape Naver web search with pagination.

    Args:
        query: Search term
        max_pages: Maximum number of pages to scrape (default: 10)
        sort: Sort order (sim, date, asc, dsc)
        period: Time period filter (all, 1d, 1w, 1m, 6m, 1y)

    Returns:
        List of web search results
    """
    log.info(f"Scraping web search for query: {query}")

    # Scrape first page
    results = []
    first_url = _build_search_url(query, "web", sort=sort, period=period)
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(first_url, **BASE_CONFIG))
    first_page_result = parse_web_search(first_page)
    total_pages = first_page_result["max_pages"]
    results = first_page_result["results"]
    displayed_results = first_page_result["num_of_displayed_results"]
    if scrape_all_pages:
        pages_to_scrape = total_pages
    else:
        pages_to_scrape = min(total_pages, max_pages)

    log.info(f"Scraping {pages_to_scrape - 1} additional pages (total: {pages_to_scrape})")

    scraped_pages = 1
    if pages_to_scrape > 1:
        other_pages = [
            ScrapeConfig(
                _build_search_url(query, page=page, sort=sort, display=displayed_results, period=period),
                **BASE_CONFIG,
            )
            for page in range(2, pages_to_scrape + 1)
        ]
        async for result in SCRAPFLY.concurrent_scrape(other_pages):
            results.extend(parse_web_search(result)["results"])
            scraped_pages += 1
        log.info(f"Scraped {scraped_pages} pages (total: {pages_to_scrape})")

    return {"results": results, "max_pages": total_pages}
