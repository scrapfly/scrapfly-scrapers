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


class SearchWebResult(TypedDict):
    """type hint for scraped web search result data"""
    title: str
    url: str
    snippet: str
    source: str
    rank: int

class SearchImageResult(TypedDict):
    """type hint for scraped image search result data"""
    title: str
    link: str
    source: str
    image_url: str
    thumbnail_url: str
    img_id: str
    color: str
    date: str
    writer: str
    domain: str
    rank: int

# Helper functions for parsing
def _extract_json_from_html(content: str, start_pos: int) -> Optional[str]:
    """
    Extract a balanced JSON object from HTML content starting at a given position.
    
    Args:
        content: HTML content string
        start_pos: Starting position (should point to opening brace)
    
    Returns:
        Extracted JSON string or None if extraction fails
    """
    brace_count = 0
    in_string = False
    escape = False
    
    for i in range(start_pos, len(content)):
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
                    return content[start_pos : i + 1]
    
    return None


def _js_to_json(js_str: str) -> str:
    """
    Convert JavaScript object notation to valid JSON.
    Handles unquoted property names and trailing commas.
    
    Args:
        js_str: JavaScript object string
    
    Returns:
        Valid JSON string
    """
    # Replace unquoted property names with quoted ones
    # Only match property names that appear after { or , or newline (start of property definition)
    # Pattern: (whitespace or { or ,) followed by unquoted word followed by :
    js_str = re.sub(r'([{,\s])([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:', r'\1"\2":', js_str)
    
    # Remove trailing commas before closing braces/brackets
    js_str = re.sub(r',(\s*[}\]])', r'\1', js_str)
    
    return js_str


# Parsing functions
def parse_web_search(result: ScrapeApiResponse) -> dict[str, Any]:
    """
    Parse web search results from JSON embedded in HTML.

    Args:
        result: ScrapFly API response

    Returns:
        Dictionary containing results and max_pages
    """
    content = result.content
    selector = result.selector
    results: List[SearchWebResult] = []

    # Extract JSON from entry.bootstrap
    pattern = r"entry\.bootstrap\([^,]+,\s*\{"
    match = re.search(pattern, content)

    if match:
        json_start = content.index("{", match.end() - 1)
        json_str = _extract_json_from_html(content, json_start)

        # Parse JSON and extract results
        try:
            if json_str:
                data = json.loads(json_str)
            else:
                return {"results": [], "max_pages": None, "num_of_displayed_results": 0}
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
    max_pages = 1
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
    log.info(f"Max pages: {max_pages}")
    log.info(f"Number of displayed results: {num_of_displayed_results}")
    return {"results": results, "max_pages": max_pages, "num_of_displayed_results": num_of_displayed_results}


def parse_image_search(result: ScrapeApiResponse) -> Dict[str, Any]:
    """
    Parse image search results from JSON embedded in HTML.
    
    Args:
        result: ScrapFly API response
        
    Returns:
        Dictionary containing image results and pagination info
    """
    content = result.content
    selector = result.selector
    results: List[SearchImageResult] = []
    data = None
    # Check if no results found (not_found02 element)
    not_found = selector.css("div.not_found02")
    if not_found:
        log.info("No search results found (not_found02 element detected)")
        return {
            "results": [],
            "num_of_displayed_results": -1,
        }
    # Extract JSON from imageSearchTabData variable
    pattern = r"var\s+imageSearchTabData\s*=\s*\{"
    match = re.search(pattern, content)
    
    if match:
        json_start = content.index("{", match.end() - 1)
        js_str = _extract_json_from_html(content, json_start)
        
        # Parse JSON and extract image results
        try:
            if js_str:
                # Convert JavaScript object notation to valid JSON
                json_str = _js_to_json(js_str)
                data = json.loads(json_str)
                items = data.get("content", {}).get("items", [])
                
                for idx, item in enumerate(items, 1):
                    if item.get("type") != "image":
                        continue
                    
                    # Extract main image URL from viewerThumb
                    viewer_thumb = item.get("viewerThumb", "")
                    
                    # Extract thumbnail URL (often in profileImg or a thumbnail field)
                    thumbnail = item.get("thumbnail", viewer_thumb)
                    
                    # Clean title by removing HTML marks
                    title = item.get("title", "").replace("<mark>", "").replace("</mark>", "")
                    
                    results.append(
                        {
                            "title": title,
                            "link": item.get("link", ""),
                            "source": item.get("source", ""),
                            "image_url": viewer_thumb,
                            "thumbnail_url": thumbnail,
                            "img_id": item.get("imgId", ""),
                            "color": item.get("color", ""),
                            "date": item.get("dateInfo", ""),
                            "writer": item.get("writerTitle", ""),
                            "domain": item.get("tld", ""),
                            "rank": idx,
                        }
                    )
                    
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.error(f"JSON parsing error: {e}")
            log.debug(f"Failed to parse JavaScript object. First 500 chars: {js_str[:500] if js_str else 'None'}")

    
    num_of_displayed_results = len(results)
    log.info(f"Number of displayed image results: {num_of_displayed_results}")
    
    return {
        "results": results,
        "num_of_displayed_results": num_of_displayed_results,
    }

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

async def scrape_image_search(
    query: str,
    max_pages: int = 3,
    sort: Optional[SortType] = None,
    period: Optional[PeriodType] = None,
    scrape_all_pages: bool = False,
) -> dict[str, Any]:
    """
    Scrape Naver image search with pagination.
    Note: Naver image search doesn't have pagination info it uses scroll to load more results but we can still scraping by using start parameter in re.

    Args:
        query: Search term
        max_pages: Maximum number of pages to scrape (default: 3)
        sort: Sort order (sim, date, asc, dsc)
        period: Time period filter (all, 1d, 1w, 1m, 6m, 1y)
        scrape_all_pages: If True, scrape all available pages

    Returns:
        Dictionary with image search results and pagination info
    """
    log.info(f"Scraping image search for query: {query}")

    # Scrape first page
    results: List[SearchImageResult] = []
    first_url = _build_search_url(query, search_type="image", sort=sort, period=period)
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(first_url, **BASE_CONFIG))
    
    first_page_result = parse_image_search(first_page)
    results = first_page_result["results"]
    displayed_results = first_page_result["num_of_displayed_results"]

    scraped_pages = 1
    
    if scrape_all_pages:
        page = 2
        
        while True:
            page_url = _build_search_url(
                query, search_type="image", page=page, sort=sort, display=displayed_results, period=period
            )
            page_result = await SCRAPFLY.async_scrape(ScrapeConfig(page_url, **BASE_CONFIG))
            page_data = parse_image_search(page_result)
            current_displayed_results = page_data["num_of_displayed_results"]
            
            scraped_pages += 1
            page += 1
            if current_displayed_results == -1 or scraped_pages == 20: # safely check max 20 page 
                break
            results.extend(page_data["results"])
    else:
        # Scrape up to max_pages
        if max_pages > 1:
            other_pages = [
                ScrapeConfig(
                    _build_search_url(query, search_type="image", page=page, sort=sort, display=displayed_results, period=period),
                    **BASE_CONFIG,
                )
                for page in range(2, max_pages + 1)
            ]
            async for result in SCRAPFLY.concurrent_scrape(other_pages):
                scraped_pages += 1
                page_data = parse_image_search(result)
                current_displayed_results = page_data["num_of_displayed_results"]
                if current_displayed_results == -1 or scraped_pages == 20: # safely check max 20 page 
                    break
                results.extend(page_data["results"])
    
    log.info(f"Scraped {scraped_pages} pages")
    return {"results": results}