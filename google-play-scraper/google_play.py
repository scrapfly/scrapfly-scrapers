"""
This is an example web scraper for play.google.com (Google Play Store).

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import re
import json
from enum import IntEnum
from html import unescape
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote, urlencode, urlparse
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse, ScrapflyScrapeError

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "US",
}

MAX_REVIEWS_PER_FETCH = 4500


class Sort(IntEnum):
    MOST_RELEVANT = 1
    NEWEST = 2
    RATING = 3


_SCRIPT_RE = re.compile(r"AF_initDataCallback[\s\S]*?</script")
_KEY_RE = re.compile(r"(ds:.*?)'")
_VALUE_RE = re.compile(r"data:([\s\S]*?), sideChannel: {}}\);<\/")
_REVIEWS_XSSI_RE = re.compile(r"\)]}'\n\n([\s\S]+)")


def _nested_get(obj: Any, path: List[int], default: Any = None) -> Any:
    current = obj
    for index in path:
        try:
            current = current[index]
        except (IndexError, KeyError, TypeError):
            return default
    return current


def _unescape_text(value: Optional[str]) -> Optional[str]:
    return unescape(value.replace("<br>", "\r\n")) if value else value


def _parse_af_init_data(html: str) -> Dict:
    """extract AF_initDataCallback ds:N datasets embedded in Play Store HTML"""
    dataset = {}
    for match in _SCRIPT_RE.findall(html):
        keys, values = _KEY_RE.findall(match), _VALUE_RE.findall(match)
        if keys and values:
            try:
                dataset[keys[0]] = json.loads(values[0])
            except json.JSONDecodeError:
                continue
    return dataset


def parse_app(response: ScrapeApiResponse) -> Dict:
    """parse app detail"""
    dataset = _parse_af_init_data(response.content)
    app = _nested_get(dataset, ["ds:5", 1, 2]) or []
    price = _nested_get(app, [57, 0, 0, 0, 0, 1, 0, 0]) or 0
    description = _nested_get(app, [12, 0, 0, 1]) or _nested_get(app, [72, 0, 1])
    histogram = _nested_get(app, [51, 1]) or []
    screenshots = _nested_get(app, [78, 0]) or []
    developer_id = _nested_get(app, [68, 1, 4, 2])
    genre = _nested_get(app, [79, 0, 0, 0])
    genre_id = _nested_get(app, [79, 0, 0, 2])
    ads = _nested_get(app, [48])
    comments = _nested_get(dataset, ["ds:8", 0]) or []
    requested_url = response.config["url"]

    return {
        "title": _nested_get(app, [0, 0]),
        "description": _unescape_text(description),
        "descriptionHTML": description,
        "summary": _unescape_text(_nested_get(app, [73, 0, 1])),
        "installs": _nested_get(app, [13, 0]),
        "minInstalls": _nested_get(app, [13, 1]),
        "realInstalls": _nested_get(app, [13, 2]),
        "score": _nested_get(app, [51, 0, 1]),
        "ratings": _nested_get(app, [51, 2, 1]),
        "reviews": _nested_get(app, [51, 3, 1]),
        "histogram": [histogram[i][1] for i in range(1, 6)] if len(histogram) > 5 else [0] * 5,
        "price": (price / 1_000_000) or 0,
        "free": price == 0,
        "currency": _nested_get(app, [57, 0, 0, 0, 0, 1, 0, 1]),
        "offersIAP": bool(_nested_get(app, [19, 0])),
        "inAppProductPrice": _nested_get(app, [19, 0]),
        "developer": _nested_get(app, [68, 0]),
        "developerId": developer_id.split("id=")[-1] if developer_id else None,
        "developerEmail": _nested_get(app, [69, 1, 0]),
        "developerWebsite": _nested_get(app, [69, 0, 5, 2]),
        "developerAddress": _nested_get(app, [69, 2, 0]),
        "privacyPolicy": _nested_get(app, [99, 0, 5, 2]),
        "genre": genre,
        "genreId": genre_id,
        "categories": [{"name": genre, "id": genre_id}] if genre else [],
        "icon": _nested_get(app, [95, 0, 3, 2]),
        "headerImage": _nested_get(app, [96, 0, 3, 2]),
        "screenshots": [item[3][2] for item in screenshots],
        "video": _nested_get(app, [100, 0, 0, 3, 2]),
        "videoImage": _nested_get(app, [100, 1, 0, 3, 2]),
        "contentRating": _nested_get(app, [9, 0]),
        "contentRatingDescription": _nested_get(app, [9, 2, 1]),
        "adSupported": bool(ads) if ads is not None else None,
        "containsAds": bool(ads),
        "released": _nested_get(app, [10, 0]),
        "lastUpdatedOn": _nested_get(app, [145, 0, 0]),
        "updated": _nested_get(app, [145, 0, 1, 0]),
        "version": _nested_get(app, [140, 0, 0, 0]) or "Varies with device",
        "comments": [item[4] for item in comments],
        "appId": parse_qs(urlparse(requested_url).query).get("id", [None])[0],
        "url": response.scrape_result.get("url") or requested_url,
    }


def parse_reviews_response(response: ScrapeApiResponse) -> Tuple[List[Dict], Optional[str]]:
    """parse batchexecute reviews payload"""
    match = _REVIEWS_XSSI_RE.findall(response.content)
    if not match:
        return [], None

    payload = json.loads(json.loads(match[0])[0][2])
    reviews = []
    for item in payload[0] or []:
        if not item or not item[0]:
            continue
        reviews.append({
            "reviewId": item[0],
            "userName": _nested_get(item, [1, 0]),
            "userImage": _nested_get(item, [1, 1, 3, 2]),
            "content": _nested_get(item, [4]),
            "score": _nested_get(item, [2]),
            "thumbsUpCount": _nested_get(item, [6]),
            "reviewCreatedVersion": _nested_get(item, [10]),
            "at": _nested_get(item, [5, 0]),
            "replyContent": _nested_get(item, [7, 1]),
            "repliedAt": _nested_get(item, [7, 2, 0]),
            "appVersion": _nested_get(item, [10]),
        })

    token = payload[-2][-1] if len(payload) >= 2 and isinstance(payload[-2], list) and payload[-2] else None
    return reviews, None if isinstance(token, list) else token


def parse_search(response: ScrapeApiResponse) -> List[Dict]:
    """parse search results"""
    dataset = _parse_af_init_data(response.content)
    sections = _nested_get(dataset, ["ds:4", 0, 1]) or []

    cards = None
    for idx in range(len(sections)):
        cards = _nested_get(sections, [idx, 22, 0])
        if isinstance(cards, list) and cards:
            break
    if not cards:
        return []

    results = []
    for entry in cards:
        card = entry[0] if entry else None
        if not card:
            continue
        price = _nested_get(card, [8, 1, 0, 0]) or 0
        description = _nested_get(card, [13, 1])
        screenshots = _nested_get(card, [2]) or []
        results.append({
            "appId": card[0][0],
            "icon": _nested_get(card, [1, 3, 2]),
            "screenshots": [item[3][2] for item in screenshots],
            "title": _nested_get(card, [3]),
            "score": _nested_get(card, [4, 1]),
            "genre": _nested_get(card, [5]),
            "price": (price / 1_000_000) or 0,
            "free": price == 0,
            "currency": _nested_get(card, [8, 1, 0, 1]),
            "video": _nested_get(card, [12, 0, 0, 3, 2]),
            "videoImage": _nested_get(card, [12, 0, 3, 3, 2]),
            "description": _unescape_text(description),
            "descriptionHTML": description,
            "developer": _nested_get(card, [14]),
            "installs": _nested_get(card, [15]),
        })
    return results



async def scrape_apps(app_ids: List[str], lang: str = "en", country: str = "us") -> List[Dict]:
    """scrape Google Play app detail pages"""
    to_scrape = [
        ScrapeConfig(url=f"https://play.google.com/store/apps/details?id={app_id}&hl={lang}&gl={country}", **BASE_CONFIG)
        for app_id in app_ids
    ]
    apps = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        if isinstance(response, ScrapflyScrapeError):
            log.error("failed to scrape app: {}", response.error)
            continue
        try:
            apps.append(parse_app(response))
        except Exception as e:
            log.error("failed to parse app: {}", e)
    log.success("scraped {} apps", len(apps))
    return apps


async def scrape_reviews(
    app_id: str,
    lang: str = "en",
    country: str = "us",
    sort: Sort = Sort.NEWEST,
    max_reviews: int = 100,
    filter_score_with: Optional[int] = None,
) -> List[Dict]:
    """scrape app reviews via the Play Store batchexecute endpoint"""
    url = f"https://play.google.com/_/PlayStoreUi/data/batchexecute?hl={lang}&gl={country}"
    reviews, seen_ids, token = [], set(), None

    while len(reviews) < max_reviews:
        count = min(max_reviews - len(reviews), MAX_REVIEWS_PER_FETCH)
        pagination = [count, None, token] if token is not None else [count]
        filters = [None, filter_score_with, None, None, None, None, None, None, None]
        inner = json.dumps([None, [2, sort.value, pagination, None, filters], [app_id, 7]], separators=(",", ":"))
        body = "f.req=" + quote(json.dumps([[["oCPfdb", inner, None, "generic"]]], separators=(",", ":")) + "\n")
        response = await SCRAPFLY.async_scrape(
            ScrapeConfig(
                url=url,
                method="POST",
                headers={"content-type": "application/x-www-form-urlencoded"},
                body=body,
                **BASE_CONFIG,
            )
        )
        page_reviews, token = parse_reviews_response(response)
        for review in page_reviews:
            if review["reviewId"] in seen_ids:
                continue
            seen_ids.add(review["reviewId"])
            reviews.append(review)
        if token is None or not page_reviews:
            break

    log.success("scraped {} reviews for {}", len(reviews), app_id)
    return reviews


async def scrape_search(query: str, lang: str = "en", country: str = "us") -> List[Dict]:
    """scrape Google Play search results"""
    params = urlencode({"q": query, "c": "apps", "hl": lang, "gl": country})
    url = f"https://play.google.com/store/search?{params}"
    print(url)
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    results = parse_search(response)
    log.success("scraped {} search results for '{}'", len(results), query)
    return results


