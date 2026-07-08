"""
This is an example web scraper for pinterest.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TypedDict
from urllib.parse import parse_qs, quote, urlencode, urlparse
from uuid import uuid4

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "proxy_pool": "public_residential_pool",
}



BASE_URL = "https://www.pinterest.com/search/pins/"
SEARCH_API_URL = "https://www.pinterest.com/resource/BaseSearchResource/get/"


class PinResult(TypedDict):
    pin_id: str
    url: str
    title: str
    description: Optional[str]
    alt_text: Optional[str]
    image: Optional[str]
    image_thumb: Optional[str]
    destination_link: Optional[str]
    video_url: Optional[str]
    is_product: bool
    board: Optional[str]
    owner: Optional[str]


class PinSearch(TypedDict):
    query: str
    search_date: str
    pins: List[PinResult]


def build_url(query: str) -> str:
    """Generate a Pinterest search URL for the given query."""
    return BASE_URL + "?" + urlencode({"q": query})


def build_post_payload(query: str, bookmark: str | None = None, search_call: dict | None = None) -> str:
    """Build urlencoded POST body for the Pinterest search API."""
    if search_call and bookmark:
        body = search_call.get("body")
        if body:
            parsed = parse_qs(body, keep_blank_values=True)
        else:
            parsed = parse_qs(urlparse(search_call["url"]).query, keep_blank_values=True)

        if parsed.get("data"):
            data = json.loads(parsed["data"][0])
            data["options"]["bookmarks"] = [bookmark]
            return urlencode({
                "source_url": parsed["source_url"][0],
                "data": json.dumps(data, separators=(",", ":")),
            })

    options: Dict[str, Any] = {
        "query": query,
        "scope": "pins",
        "appliedProductFilters": "---",
        "redux_normalize_feed": True,
    }
    if bookmark:
        options["bookmarks"] = [bookmark]

    return urlencode({
        "source_url": f"/search/pins/?q={quote(query)}",
        "data": json.dumps({"options": options, "context": {}}, separators=(",", ":")),
    })


def get_search_call(response: ScrapeApiResponse) -> Tuple[dict, dict]:
    """Extract the search API XHR call and headers from captured browser data."""
    xhr_calls = response.scrape_result["browser_data"]["xhr_call"]
    search_calls = [call for call in xhr_calls if "BaseSearchResource/get" in call["url"]]
    if not search_calls:
        raise ValueError("Could not find BaseSearchResource/get XHR call")
    search_call = search_calls[-1]
    return search_call, search_call["headers"]


def parse_search_results(pages: List[dict] | dict, query: str) -> PinSearch:
    """Parse raw Pinterest search API responses into a normalized result set."""
    pins: List[PinResult] = []
    for page in pages if isinstance(pages, list) else [pages]:
        for pin in page.get("resource_response", {}).get("data", {}).get("results", []):
            if pin.get("type") != "pin" or not (pin_id := pin.get("id")):
                continue
            images = pin.get("images") or {}
            videos = (pin.get("videos") or {}).get("video_list") or {}
            pins.append(PinResult(
                pin_id=str(pin_id),
                url=f"https://www.pinterest.com/pin/{pin_id}/",
                title=(pin.get("title") or pin.get("grid_title") or "").strip(),
                description=pin.get("description"),
                alt_text=pin.get("auto_alt_text") or pin.get("seo_alt_text"),
                image=(images.get("orig") or {}).get("url"),
                image_thumb=(images.get("236x") or {}).get("url"),
                destination_link=pin.get("link"),
                video_url=next((v.get("url") for v in videos.values() if v.get("url")), None),
                is_product=bool(pin.get("shopping_flags")),
                board=(pin.get("board") or {}).get("name"),
                owner=(pin.get("pinner") or {}).get("username"),
            ))
    return PinSearch(query=query, search_date=datetime.now().strftime("%Y-%m-%d"), pins=pins)


async def scrape_pinterest(query: str, max_pages: int = 3) -> PinSearch:
    """Scrape Pinterest search results and return parsed pin data."""
    session_id = str(uuid4()).replace("-", "")
    url = build_url(query)
    pages: List[dict] = []

    log.info(f"scraping Pinterest search: {query}")
    first = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, session=session_id, render_js=True, auto_scroll=True,rendering_wait=8000, **BASE_CONFIG)
    )

    search_call, headers = get_search_call(first)
    headers = {**headers, "content-type": "application/x-www-form-urlencoded"}
    first_data = json.loads(search_call["response"]["body"])
    pages.append(first_data)
    bookmark = first_data.get("resource_response", {}).get("bookmark")
    log.info("page 1: captured")

    for page in range(2, max_pages + 1):
        if not bookmark:
            log.info("no more pages")
            break

        resp = await SCRAPFLY.async_scrape(
            ScrapeConfig(
                SEARCH_API_URL,
                **BASE_CONFIG,
                session=session_id,
                method="POST",
                headers=headers,
                body=build_post_payload(query, bookmark=bookmark, search_call=search_call),
                render_js=False,
            )
        )
        data = json.loads(resp.content)
        pages.append(data)
        bookmark = data.get("resource_response", {}).get("bookmark")
        log.info(f"page {page}: captured")

    log.success(f"scraped {len(pages)} pages for query: {query}")
    return parse_search_results(pages, query)
