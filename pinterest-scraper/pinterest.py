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
    "country": "us",
}

BASE_URL = "https://www.pinterest.com"
RESOURCE_URL = f"{BASE_URL}/resource"
SEARCH_PAGE_URL = f"{BASE_URL}/search/pins/"
IMAGE_SIZE_PRIORITY = ["orig", "1200x", "736x", "564x", "474x", "236x", "170x"]
THUMB_SIZE_PRIORITY = ["236x", "170x", "474x", *IMAGE_SIZE_PRIORITY]
END_BOOKMARK = "-end-"


def build_url(path: str = "", **params) -> str:
    """Build a Pinterest URL from a path and optional query params."""
    url = f"{BASE_URL}/{path.strip('/')}/"
    return f"{url}?{urlencode(params)}" if params else url


def build_search_page_url(query: str) -> str:
    """Generate a Pinterest search URL for the given query."""
    return SEARCH_PAGE_URL + "?" + urlencode({"q": query})


def url_path_parts(url: str) -> List[str]:
    """split a URL (or bare path) into its non-empty path segments"""
    return [part for part in urlparse(url).path.split("/") if part]


def parse_pin_id(pin_url: str) -> str:
    """extract the numeric pin ID from a pin URL, a slugged pin URL or a bare ID"""
    if pin_url.isdigit():
        return pin_url
    parts = url_path_parts(pin_url)
    if not parts:
        raise ValueError(f"could not find a pin ID in {pin_url!r}")

    # slugged pin URLs look like /pin/some-pin-title--142567144444540246/
    return parts[-1].rsplit("--", 1)[-1]


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
    board_url: Optional[str]
    owner: Optional[str]
    domain: Optional[str]
    save_count: Optional[int]
    created_at: Optional[str]


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


def _clean(value: Any) -> Optional[str]:
    """strip a text field and turn blanks into None"""
    return value.strip() or None if isinstance(value, str) else None


def _pick_image(images: Dict[str, Any], sizes: List[str]) -> Optional[str]:
    """pick the first available image URL for the given size priority list"""
    for size in sizes:
        if isinstance(images.get(size), dict) and images[size].get("url"):
            return images[size]["url"]
    return next((img["url"] for img in images.values() if isinstance(img, dict) and img.get("url")), None)


def _pick_video(pin: Dict[str, Any]) -> Optional[str]:
    """pick a pin's video URL, preferring a progressive MP4 over an HLS playlist"""
    video_lists = [(pin.get("videos") or {}).get("video_list") or {}]
    for page in (pin.get("story_pin_data") or {}).get("pages") or []:
        for block in page.get("blocks") or []:
            video_lists.append((block.get("video") or {}).get("video_list") or {})
    urls = [v["url"] for video_list in video_lists for v in video_list.values() if isinstance(v, dict) and v.get("url")]
    return next((url for url in urls if ".mp4" in url), urls[0] if urls else None)


def parse_pin_item(pin: Any) -> Optional[PinResult]:
    """normalize a raw Pinterest pin object (from any feed or resource) into PinResult"""
    if not isinstance(pin, dict) or pin.get("type") != "pin" or not (pin_id := pin.get("id")):
        return None
    board = pin.get("board") or {}
    # feeds expose different title/description fields depending on the field_set_key
    title = _clean(pin.get("title")) or _clean(pin.get("grid_title")) or _clean(pin.get("seo_title"))
    description = (
        _clean(pin.get("description"))
        or _clean(pin.get("closeup_unified_description"))
        or _clean(pin.get("closeup_description"))
    )
    return PinResult(
        pin_id=str(pin_id),
        url=build_url(f"pin/{pin_id}"),
        title=title or "",
        description=description,
        alt_text=_clean(pin.get("auto_alt_text")) or _clean(pin.get("seo_alt_text")) or _clean(pin.get("alt_text")),
        image=_pick_image(pin.get("images") or {}, IMAGE_SIZE_PRIORITY),
        image_thumb=_pick_image(pin.get("images") or {}, THUMB_SIZE_PRIORITY),
        destination_link=pin.get("link") or pin.get("tracked_link"),
        video_url=_pick_video(pin),
        is_product=bool(pin.get("shopping_flags")) or bool(pin.get("product_metadata")),
        board=board.get("name"),
        board_url=build_url(board["url"]) if board.get("url") else None,
        owner=(pin.get("pinner") or {}).get("username") or (pin.get("native_creator") or {}).get("username"),
        domain=pin.get("domain") or pin.get("link_domain"),
        save_count=pin.get("repin_count"),
        created_at=pin.get("created_at"),
    )


def parse_pin_items(items: List[Any]) -> List[PinResult]:
    """normalize a feed's raw items, dropping non-pin entries (ads modules, story racks)"""
    return [pin for item in items if (pin := parse_pin_item(item))]


def assert_not_stubs(items: List[Any], context: str) -> None:
    """fail loudly when a feed hands back image-only pin stubs instead of full pins

    Pinterest gates its feeds by default, which strips every field except the
    images - silently returning pins with no title/description/board is worse
    than raising, so this makes the regression obvious.
    """
    raw_pins = [item for item in items if isinstance(item, dict) and item.get("type") == "pin"]
    if raw_pins and not any(
        pin.get("title") or pin.get("grid_title") or pin.get("description") or pin.get("board") for pin in raw_pins
    ):
        raise RuntimeError(f"{context} returned pin stubs without metadata - the ungated option is no longer honoured")


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


async def fetch_resource(
    session_id: str,
    resource_name: str,
    source_url: str,
    options: Dict[str, Any],
    headers: Dict[str, str],
) -> Dict[str, Any]:
    """call Pinterest's internal /resource/<Name>/get/ API and return its resource_response"""
    params = {
        "source_url": source_url,
        "data": json.dumps({"options": options, "context": {}}, separators=(",", ":")),
    }
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            f"{RESOURCE_URL}/{resource_name}/get/?" + urlencode(params),
            session=session_id,
            render_js=False,
            headers=headers,
            **BASE_CONFIG,
        )
    )
    try:
        return json.loads(response.content)["resource_response"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RuntimeError(f"{resource_name} did not return a resource_response: {response.content[:200]}") from exc


async def paginate_resource(
    session_id: str,
    resource_name: str,
    source_url: str,
    options: Dict[str, Any],
    headers: Dict[str, str],
    max_pages: int,
) -> List[dict]:
    """paginate a Pinterest resource feed (board/profile pins) reusing a bootstrapped session"""
    items: List[dict] = []
    bookmark: Optional[str] = None
    seen_bookmarks = set()

    for page in range(1, max_pages + 1):
        page_options = {**options, "gated": False}
        if bookmark:
            page_options["bookmarks"] = [bookmark]
        resource_response = await fetch_resource(session_id, resource_name, source_url, page_options, headers)
        data = resource_response.get("data")
        if not isinstance(data, list):
            raise RuntimeError(
                f"{resource_name} page {page} returned no feed data "
                f"(status={resource_response.get('status')!r}, message={resource_response.get('message')!r})"
            )
        if not data:
            log.info(f"{resource_name}: page {page} is empty, stopping")
            break
        assert_not_stubs(data, f"{resource_name} page {page}")

        items.extend(data)
        log.info(f"{resource_name}: page {page} captured ({len(items)} items so far)")
        bookmark = resource_response.get("bookmark")
        if not bookmark or bookmark == END_BOOKMARK or bookmark in seen_bookmarks:
            log.info(f"{resource_name}: no more pages")
            break
        seen_bookmarks.add(bookmark)
    return items


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
        results = page.get("resource_response", {}).get("data", {}).get("results") or []
        pins.extend(parse_pin_items(results))
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
        assert_not_stubs(results, f"search page {page}")

        pages.append(data)
        log.info(f"page {page}: scraped {len(results)} results")
        bookmark = resource_response.get("bookmark")
        if not bookmark or bookmark == END_BOOKMARK or bookmark in seen_bookmarks:
            log.info("no more pages")
            break
        seen_bookmarks.add(bookmark)

    search = parse_search_results(pages, query)
    log.success(f"scraped {len(search['pins'])} pins for query: {query}")
    return search


async def scrape_board(board_url: str, max_pages: int = 3) -> BoardScrape:
    """scrape a Pinterest board's metadata and pins"""
    session_id = str(uuid4()).replace("-", "")
    path_parts = url_path_parts(board_url)

    log.info(f"scraping Pinterest board: {board_url}")
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(board_url, session=session_id, render_js=True, auto_scroll=True, rendering_wait=6000, **BASE_CONFIG)
    )
    app_version, resources = extract_page_data(response.content)
    board_options, board_entry = get_resource_entry(resources, "BoardResource")
    board_data = board_entry["data"]
    feed_options, _ = get_resource_entry(resources, "BoardFeedResource")

    headers = build_session_headers(response, app_version, board_url)
    raw_pins = await paginate_resource(
        session_id=session_id,
        resource_name="BoardFeedResource",
        source_url=board_url,
        options=feed_options,
        headers=headers,
        max_pages=max_pages,
    )
    pins = parse_pin_items(raw_pins)

    owner = board_data.get("owner") or {}
    log.success(f"scraped board {board_url} with {len(pins)} pins")
    return BoardScrape(
        # the resource options carry the board's canonical /<username>/<slug>/ pair
        username=board_options.get("username") or owner.get("username") or (path_parts[0] if path_parts else board_url),
        board_slug=board_options.get("slug") or (path_parts[1] if len(path_parts) > 1 else board_url),
        board_name=board_data.get("name") or board_options.get("slug") or board_url,
        description=_clean(board_data.get("description")),
        pin_count=board_data.get("pin_count"),
        follower_count=board_data.get("follower_count"),
        url=build_url(board_data["url"]) if board_data.get("url") else board_url,
        pins=pins,
    )


async def scrape_profile(username: str, max_pages: int = 3) -> ProfileScrape:
    """scrape a Pinterest user's profile metadata and their pins"""
    session_id = str(uuid4()).replace("-", "")
    profile_url = username if "pinterest.com" in username else build_url(username)
    username = next(iter(url_path_parts(profile_url)), username)

    log.info(f"scraping Pinterest profile: {profile_url}")
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(profile_url, session=session_id, render_js=True, auto_scroll=True, rendering_wait=6000, **BASE_CONFIG)
    )
    app_version, resources = extract_page_data(response.content)
    _, user_entry = get_resource_entry(resources, "UserResource")
    user_data = user_entry["data"]
    feed_options, _ = get_resource_entry(resources, "UserPinsResource")

    headers = build_session_headers(response, app_version, profile_url)
    raw_pins = await paginate_resource(
        session_id=session_id,
        resource_name="UserPinsResource",
        source_url=profile_url,
        options=feed_options,
        headers=headers,
        max_pages=max_pages,
    )
    pins = parse_pin_items(raw_pins)

    log.success(f"scraped profile {username} with {len(pins)} pins")
    return ProfileScrape(
        username=user_data.get("username") or username,
        full_name=user_data.get("full_name") or user_data.get("first_name"),
        # `about` is the user-written bio, seo_description only prefixes it with the name
        bio=_clean(user_data.get("about")) or _clean(user_data.get("seo_description")),
        follower_count=user_data.get("follower_count"),
        following_count=user_data.get("following_count"),
        pin_count=user_data.get("pin_count"),
        profile_image=user_data.get("image_xlarge_url") or user_data.get("image_medium_url"),
        url=profile_url,
        pins=pins,
    )


async def scrape_pin(pin_url: str) -> PinDetail:
    """scrape a single Pinterest pin's details"""
    session_id = str(uuid4()).replace("-", "")
    pin_id = parse_pin_id(pin_url)
    pin_url = build_url(f"pin/{pin_id}")

    log.info(f"scraping Pinterest pin: {pin_url}")
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(pin_url, session=session_id, render_js=True, rendering_wait=5000, **BASE_CONFIG)
    )
    # deleted or private pins quietly bounce to the /ideas/ feed instead of 404ing
    landed = response.scrape_result.get("url") or pin_url
    if f"/pin/{pin_id}" not in urlparse(landed).path:
        raise ValueError(f"pin {pin_id} did not resolve - Pinterest redirected to {landed}, the pin is likely deleted or private")

    app_version, _ = extract_page_data(response.content)
    headers = build_session_headers(response, app_version, pin_url)
    resource_response = await fetch_resource(
        session_id=session_id,
        resource_name="PinResource",
        source_url=f"/pin/{pin_id}/",
        options={"id": pin_id, "field_set_key": "unauth_react_main_pin", "fetch_visual_search_objects": False},
        headers=headers,
    )
    data = resource_response.get("data")
    pin = parse_pin_item(data)
    if pin is None:
        raise RuntimeError(
            f"PinResource returned no pin for {pin_id} "
            f"(status={resource_response.get('status')!r}, message={resource_response.get('message')!r})"
        )

    log.success(f"scraped pin {pin_id}")
    return PinDetail(
        **pin,
        images={size: img["url"] for size, img in (data.get("images") or {}).items() if isinstance(img, dict) and img.get("url")},
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
