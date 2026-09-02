"""
This is an example web scraper for pinterest.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import base64
import json
import os
import re
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, TypedDict
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from uuid import uuid4

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    "asp": True,
    "proxy_pool": "public_residential_pool",
}

BASE_URL = "https://www.pinterest.com"
RESOURCE_URL = f"{BASE_URL}/resource"
SEARCH_PAGE_URL = f"{BASE_URL}/search/pins/"
IMAGE_SIZE_PRIORITY = ["orig", "1200x", "736x", "474x", "236x", "170x"]


def build_url(path: str = "", **params) -> str:
    """Build a Pinterest URL from a path and optional query params."""
    url = f"{BASE_URL}/{path.strip('/')}/"
    return f"{url}?{urlencode(params)}" if params else url


def build_search_page_url(query: str) -> str:
    """Generate a Pinterest search URL for the given query."""
    return SEARCH_PAGE_URL + "?" + urlencode({"q": query})


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
    image_base64: Optional[str]
    success: bool


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


def _pick_image(images: Dict[str, Any], sizes: List[str]) -> Optional[str]:
    """pick the first available image URL for the given size priority list"""
    for size in sizes:
        if images.get(size):
            return images[size]["url"]
    return next(iter(images.values()))["url"] if images else None


def parse_pin_item(pin: Any) -> Optional[PinResult]:
    """normalize a raw Pinterest pin object (from board/profile feeds) into PinResult"""
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


async def scrape_search(query: str, max_pages: int = 3) -> PinSearch:
    """Scrape Pinterest search results and return parsed pin data."""
    session_id = str(uuid4()).replace("-", "")
    pages: List[dict] = []
    bookmark: Optional[str] = None
    seen_bookmarks = set()

    log.info(f"scraping Pinterest search: {query}")
    first = await SCRAPFLY.async_scrape(
        ScrapeConfig(build_search_page_url(query), session=session_id, render_js=True, auto_scroll=True, rendering_wait=8000, **BASE_CONFIG)
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


def _content_to_base64(content: Any) -> str:
    """normalize Scrapfly binary/text content into a base64 string"""
    if isinstance(content, BytesIO):
        return base64.b64encode(content.getvalue()).decode("ascii")
    if isinstance(content, bytes):
        return base64.b64encode(content).decode("ascii")
    return content


async def download_pin_images(pins: List[Dict[str, Any]]) -> List[DownloadResult]:
    """download the best-quality image for each scraped pin and return it as base64"""
    results: List[DownloadResult] = []

    for pin in pins:
        pin_id = str(pin.get("pin_id") or "unknown")
        image_url = pin.get("image") or pin.get("image_thumb")
        image_base64 = None

        if image_url:
            try:
                resp = await SCRAPFLY.async_scrape(ScrapeConfig(image_url, **BASE_CONFIG))
                image_base64 = _content_to_base64(resp.scrape_result["content"])
            except Exception as e:
                log.error(f"failed to download pin {pin_id} image: {e}")
                image_base64 = None

        results.append(
            DownloadResult(
                pin_id=pin_id,
                url=image_url or "",
                image_base64=image_base64,
                success=bool(image_base64),
            )
        )

    log.success(f"downloaded {sum(r['success'] for r in results)}/{len(results)} pin images as base64")
    return results
