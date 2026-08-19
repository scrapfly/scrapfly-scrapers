"""
This is an example web scraper for pinterest.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
from datetime import datetime
from typing import List, Optional, Tuple, TypedDict
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
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


def build_search_url(search_call: dict, bookmark: Optional[str] = None) -> str:
    """Rebuild the captured search API URL for one page of results.

    The browser issues this call gated, which returns image-only pin stubs, so
    ungate it to get the full pin metadata.
    """
    parts = urlparse(search_call["url"])
    params = {key: values[0] for key, values in parse_qs(parts.query, keep_blank_values=True).items()}
    params.pop("_", None)  # per-request cache buster, stale once replayed
    try:
        data = json.loads(params["data"])
        data["options"]["gated"] = False
        # the captured call can already be paginated, so always set the bookmark
        data["options"]["bookmarks"] = [bookmark] if bookmark else []
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"unexpected search XHR shape: {search_call['url'][:200]}") from exc
    params["data"] = json.dumps(data, separators=(",", ":"))
    return urlunparse(parts._replace(query=urlencode(params)))


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
                description=(pin.get("description") or "").strip() or None,
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
    pages: List[dict] = []
    bookmark: Optional[str] = None
    seen_bookmarks = set()

    log.info(f"scraping Pinterest search: {query}")
    first = await SCRAPFLY.async_scrape(
        ScrapeConfig(build_url(query), session=session_id, render_js=True, auto_scroll=True, rendering_wait=8000, **BASE_CONFIG)
    )
    search_call, headers = get_search_call(first)
    # the browser's own response is gated, so every page is refetched ungated below

    for page in range(1, max_pages + 1):
        resp = await SCRAPFLY.async_scrape(
            ScrapeConfig(
                build_search_url(search_call, bookmark),
                **BASE_CONFIG,
                session=session_id,  # carries the rendered page's cookies over to the API calls
                headers=headers,
                render_js=False,
            )
        )
        data = json.loads(resp.content)
        resource_response = data.get("resource_response", {})
        results = resource_response.get("data", {}).get("results")
        if results is None:
            raise RuntimeError(
                f"search API response missing results on page {page} "
                f"(status={resource_response.get('status')!r}, message={resource_response.get('message')!r})"
            )
        if not results:
            log.info(f"page {page}: no results, stopping")
            break
        pin_results = [pin for pin in results if pin.get("type") == "pin"]
        if pin_results and not any(pin.get("title") or pin.get("description") or pin.get("board") for pin in pin_results):
            raise RuntimeError(f"page {page} returned pin stubs without metadata - the ungated search option is no longer honoured")

        pages.append(data)
        log.info(f"page {page}: scraped {len(results)} results")
        bookmark = resource_response.get("bookmark")
        if not bookmark or bookmark in seen_bookmarks:
            log.info("no more pages")
            break
        seen_bookmarks.add(bookmark)

    search = parse_search_results(pages, query)
    log.success(f"scraped {len(search['pins'])} pins for query: {query}")
    return search
