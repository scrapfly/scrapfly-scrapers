"""
This is an example web scraper for pinterest.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union
from urllib.parse import parse_qs, quote, urlencode, urlparse
from uuid import uuid4

import aiohttp
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    "asp": True,
    "proxy_pool": "public_residential_pool",
    "country": "US",
}

BASE_URL = "https://www.pinterest.com"
RESOURCE_URL = f"{BASE_URL}/resource"
SEARCH_API_URL = f"{RESOURCE_URL}/BaseSearchResource/get/"
IMAGE_SIZE_PRIORITY = ["orig", "1200x", "736x", "474x", "236x", "170x"]


def build_url(path: str = "", **params) -> str:
    """Build a Pinterest URL from a path and optional query params."""
    url = f"{BASE_URL}/{path.strip('/')}/"
    return f"{url}?{urlencode(params)}" if params else url


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


class BoardScrape(TypedDict):
    username: str
    board_slug: str
    board_name: str
    description: Optional[str]
    pin_count: Optional[int]
    follower_count: Optional[int]
    url: str
    pins: List[PinResult]


class ProfileScrape(TypedDict):
    username: str
    full_name: Optional[str]
    bio: Optional[str]
    follower_count: Optional[int]
    following_count: Optional[int]
    pin_count: Optional[int]
    profile_image: Optional[str]
    url: str
    pins: List[PinResult]


class PinDetail(PinResult, total=False):
    images: Dict[str, str]
    board_url: Optional[str]


class DownloadResult(TypedDict):
    pin_id: str
    url: str
    file_path: Optional[str]
    success: bool


def _pick_image(images: Dict[str, Any], sizes: List[str]) -> Optional[str]:
    """pick the first available image URL for the given size priority list"""
    for size in sizes:
        if images.get(size):
            return images[size]["url"]
    return next(iter(images.values()))["url"] if images else None


def parse_pin_item(pin: Any) -> Optional[PinResult]:
    """normalize a raw Pinterest pin object (from search/board/profile feeds) into PinResult"""
    if not isinstance(pin, dict) or pin.get("type") != "pin" or not (pin_id := pin.get("id")):
        return None
    images = pin.get("images") or {}
    videos = (pin.get("videos") or {}).get("video_list") or {}
    return PinResult(
        pin_id=str(pin_id),
        url=build_url(f"pin/{pin_id}"),
        title=(pin.get("title") or pin.get("grid_title") or "").strip(),
        description=pin.get("description"),
        alt_text=pin.get("auto_alt_text") or pin.get("seo_alt_text") or pin.get("alt_text"),
        image=_pick_image(images, IMAGE_SIZE_PRIORITY),
        image_thumb=_pick_image(images, ["236x", "170x", "474x", *IMAGE_SIZE_PRIORITY]),
        destination_link=pin.get("link"),
        video_url=next((v.get("url") for v in videos.values() if v.get("url")), None),
        is_product=bool(pin.get("shopping_flags")),
        board=(pin.get("board") or {}).get("name"),
        owner=(pin.get("pinner") or {}).get("username"),
    )


def extract_page_data(html: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """extract Pinterest's app version and server-rendered resource cache from a page"""
    version_match = re.search(r'<script id="__PWS_DATA__" type="application/json">(.*?)</script>', html, re.S)
    app_version = json.loads(version_match.group(1)).get("appVersion") if version_match else None

    props_match = re.search(r'<script id="__PWS_INITIAL_PROPS__" type="application/json">(.*?)</script>', html, re.S)
    resources: Dict[str, Any] = {}
    if props_match:
        try:
            resources = json.loads(props_match.group(1))["initialReduxState"]["resources"]
        except (json.JSONDecodeError, KeyError):
            pass
    return app_version, resources


def get_resource_entry(resources: Dict[str, Any], resource_name: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """get the (options, cached entry) for a given Pinterest resource name from the resource cache"""
    entries = resources.get(resource_name) or {}
    if not entries:
        raise ValueError(f"Could not find {resource_name} data in page, the URL may be invalid or blocked")
    options_key = next(iter(entries))
    options = {k: v for k, v in json.loads(options_key)}
    return options, entries[options_key]


def build_session_headers(response: ScrapeApiResponse, app_version: Optional[str], referer: str) -> Dict[str, str]:
    """build the headers Pinterest expects on authenticated resource API calls"""
    cookies = response.scrape_result.get("cookies") or []
    csrftoken = next((c["value"] for c in cookies if c.get("name") == "csrftoken"), None)
    headers = {
        "accept": "application/json, text/javascript, */*, q=0.01",
        "x-requested-with": "XMLHttpRequest",
        "x-app-version": app_version or "",
        "x-pinterest-pws-handler": "www/index.js",
        "referer": referer,
    }
    if csrftoken:
        headers["x-csrftoken"] = csrftoken
    return headers


async def paginate_resource(
    session_id: str,
    resource_name: str,
    source_url: str,
    options: Dict[str, Any],
    first_page_data: List[dict],
    bookmark: Optional[str],
    headers: Dict[str, str],
    max_pages: int,
) -> List[dict]:
    """paginate a Pinterest resource feed (board/profile pins) reusing a bootstrapped session"""
    pages: List[dict] = list(first_page_data)
    page = 2
    while bookmark and page <= max_pages:
        params = {
            "source_url": source_url,
            "data": json.dumps({"options": {**options, "bookmarks": [bookmark]}, "context": {}}, separators=(",", ":")),
        }
        resp = await SCRAPFLY.async_scrape(
            ScrapeConfig(
                f"{RESOURCE_URL}/{resource_name}/get/?" + urlencode(params),
                session=session_id,
                render_js=False,
                headers=headers,
                **BASE_CONFIG,
            )
        )
        resource_response = json.loads(resp.content)["resource_response"]
        pages.extend(resource_response.get("data") or [])
        bookmark = resource_response.get("bookmark")
        log.info(f"{resource_name}: page {page} captured ({len(pages)} pins so far)")
        page += 1
    return pages


def build_post_payload(query: str, bookmark: Optional[str] = None, search_call: Optional[dict] = None) -> str:
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


def iter_search_result_items(items: List[Any]):
    """flatten Pinterest search results, unwrapping grouped "story" entries into their pin objects"""
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "story":
            yield from iter_search_result_items(item.get("objects") or [])
        else:
            yield item


def parse_search_results(pages: List[dict], query: str) -> PinSearch:
    """Parse raw Pinterest search API responses into a normalized result set."""
    pins: List[PinResult] = []
    for page in pages:
        results = page.get("resource_response", {}).get("data", {}).get("results", [])
        for raw in iter_search_result_items(results):
            if pin := parse_pin_item(raw):
                pins.append(pin)
    return PinSearch(query=query, search_date=datetime.now().strftime("%Y-%m-%d"), pins=pins)


async def scrape_pinterest(query: str, max_pages: int = 3) -> PinSearch:
    """Scrape Pinterest search results and return parsed pin data."""
    session_id = str(uuid4()).replace("-", "")
    url = build_url("search/pins", q=query)
    pages: List[dict] = []

    log.info(f"scraping Pinterest search: {query}")
    first = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, session=session_id, render_js=True, auto_scroll=True, rendering_wait=8000, **BASE_CONFIG)
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


async def scrape_board(board_url: str, max_pages: int = 3) -> BoardScrape:
    """scrape a Pinterest board's metadata and pins"""
    session_id = str(uuid4()).replace("-", "")

    log.info(f"scraping Pinterest board: {board_url}")
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(board_url, session=session_id, render_js=True, auto_scroll=True, rendering_wait=6000, **BASE_CONFIG)
    )
    app_version, resources = extract_page_data(response.content)
    _, board_entry = get_resource_entry(resources, "BoardResource")
    board_data = board_entry["data"]
    feed_options, feed_entry = get_resource_entry(resources, "BoardFeedResource")

    headers = build_session_headers(response, app_version, board_url)
    raw_pins = await paginate_resource(
        session_id=session_id,
        resource_name="BoardFeedResource",
        source_url=board_url,
        options=feed_options,
        first_page_data=feed_entry.get("data") or [],
        bookmark=feed_entry.get("nextBookmark"),
        headers=headers,
        max_pages=max_pages,
    )
    pins = [pin for raw in raw_pins if (pin := parse_pin_item(raw))]

    log.success(f"scraped board {board_url} with {len(pins)} pins")
    return BoardScrape(
        username=next((p for p in urlparse(board_url).path.split("/") if p), board_url),
        board_slug=next((p for p in urlparse(board_url).path.split("/") if p), board_url),
        board_name=board_data.get("name") or next((p for p in urlparse(board_url).path.split("/") if p), board_url),
        description=board_data.get("description") or None,
        pin_count=board_data.get("pin_count"),
        follower_count=board_data.get("follower_count"),
        url=board_url,
        pins=pins,
    )


async def scrape_profile(username: str, max_pages: int = 3) -> ProfileScrape:
    """scrape a Pinterest user's profile metadata and their pins"""
    session_id = str(uuid4()).replace("-", "")
    profile_url = username if "pinterest.com" in username else build_url(username)
    username = next((p for p in urlparse(profile_url).path.split("/") if p), username)

    log.info(f"scraping Pinterest profile: {profile_url}")
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(profile_url, session=session_id, render_js=True, auto_scroll=True, rendering_wait=6000, **BASE_CONFIG)
    )
    app_version, resources = extract_page_data(response.content)
    _, user_entry = get_resource_entry(resources, "UserResource")
    user_data = user_entry["data"]
    feed_options, feed_entry = get_resource_entry(resources, "UserPinsResource")

    headers = build_session_headers(response, app_version, profile_url)
    raw_pins = await paginate_resource(
        session_id=session_id,
        resource_name="UserPinsResource",
        source_url=profile_url,
        options=feed_options,
        first_page_data=feed_entry.get("data") or [],
        bookmark=feed_entry.get("nextBookmark"),
        headers=headers,
        max_pages=max_pages,
    )
    pins = [pin for raw in raw_pins if (pin := parse_pin_item(raw))]

    log.success(f"scraped profile {username} with {len(pins)} pins")
    return ProfileScrape(
        username=username,
        full_name=user_data.get("first_name"),
        bio=user_data.get("seo_description"),
        follower_count=user_data.get("follower_count"),
        following_count=user_data.get("following_count"),
        pin_count=user_data.get("pin_count"),
        profile_image=user_data.get("image_medium_url"),
        url=profile_url,
        pins=pins,
    )


def _text(selector, css: str) -> Optional[str]:
    """join and clean all descendant text nodes matched by a CSS selector"""
    parts = [t.strip() for t in selector.css(f"{css} ::text").getall() if t.strip()]
    return " ".join(parts) if parts else None


def _rewrite_image_size(url: Optional[str], size: str) -> Optional[str]:
    """rewrite a pinimg.com image URL to a different size variant, e.g. 736x -> originals"""
    if not url:
        return None
    return re.sub(r"/(originals|\d+x\d*)/", f"/{size}/", url, count=1)


async def scrape_pin(pin_url: str) -> PinDetail:
    """scrape a single Pinterest pin's details"""
    if "pinterest.com" not in pin_url:
        pin_url = build_url(f"pin/{pin_url}")
    pin_id = next((p for p in urlparse(pin_url).path.split("/") if p), pin_url)

    log.info(f"scraping Pinterest pin: {pin_url}")
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(pin_url, render_js=True, rendering_wait=5000, **BASE_CONFIG)
    )
    sel = response.selector

    native_image = sel.css("[data-test-id=pin-closeup-image] img::attr(src)").get()
    images = {
        "orig": _rewrite_image_size(native_image, "originals"),
        "736x": _rewrite_image_size(native_image, "736x"),
        "474x": _rewrite_image_size(native_image, "474x"),
        "236x": _rewrite_image_size(native_image, "236x"),
    }
    images = {size: url for size, url in images.items() if url}

    description = _text(sel, "[data-test-id=main-pin-description-text]")
    if description and "}" in description:
        description = description.rsplit("}", 1)[-1].strip() or None

    board_link = sel.css("[data-test-id=pin-metadata-drawer-original-board-section] a")
    board_name = (board_link.css("::text").get() or "").strip() or None
    board_href = board_link.attrib.get("href")

    owner_href = sel.css("[data-test-id=creator-profile-link]::attr(href)").get()
    owner = next((p for p in owner_href.split("/") if p), owner_href) if owner_href else _text(sel, "[data-test-id=creator-profile-name]")

    return PinDetail(
        pin_id=pin_id,
        url=pin_url,
        title=_text(sel, "[data-test-id=pinTitle]") or "",
        description=description,
        alt_text=sel.css("[data-test-id=pin-closeup-image] img::attr(alt)").get(),
        image=images.get("orig") or native_image,
        image_thumb=images.get("236x"),
        destination_link=None,
        video_url=None,
        is_product=bool(sel.css("[data-test-id=product-title]").get()),
        board=board_name,
        owner=owner,
        images=images,
        board_url=(build_url(board_href) if board_href else None),
    )


async def download_pin_images(pins: List[Dict[str, Any]], output_dir: Union[str, Path]) -> List[DownloadResult]:
    """download the best-quality image for each scraped pin to a local directory"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[DownloadResult] = []

    async with aiohttp.ClientSession() as session:
        for pin in pins:
            pin_id = str(pin.get("pin_id") or "unknown")
            image_url = pin.get("image") or pin.get("image_thumb")
            file_path = None

            if image_url:
                try:
                    async with session.get(image_url) as resp:
                        resp.raise_for_status()
                        ext = Path(urlparse(image_url).path).suffix or ".jpg"
                        file_path = output_dir / f"{pin_id}{ext}"
                        file_path.write_bytes(await resp.read())
                except Exception as e:
                    log.error(f"failed to download pin {pin_id} image: {e}")
                    file_path = None

            results.append(DownloadResult(pin_id=pin_id, url=image_url or "", file_path=str(file_path) if file_path else None, success=bool(file_path)))

    log.success(f"downloaded {sum(r['success'] for r in results)}/{len(results)} pin images to {output_dir}")
    return results
