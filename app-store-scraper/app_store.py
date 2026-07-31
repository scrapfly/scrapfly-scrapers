"""
This is an example web scraper for Apple App Store (apps.apple.com, itunes.apple.com).

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
import re
from typing import Dict, List, Optional

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "US",
}


def _label(entry: Dict, key: str) -> Optional[str]:
    """RSS feed values are wrapped like {"label": "..."}"""
    return (entry.get(key) or {}).get("label")


def parse_app_metadata(response: ScrapeApiResponse, app_id: str, country: str) -> Dict:
    """parse app metadata from the iTunes lookup API"""
    data = json.loads(response.content)
    if not data.get("resultCount"):
        raise ValueError(f"App {app_id} not found in {country} storefront")

    app = data["results"][0]
    price = app.get("price") or 0

    return {
        "appId": str(app.get("trackId", app_id)),
        "bundleId": app.get("bundleId"),
        "title": app.get("trackName"),
        "description": app.get("description"),
        "summary": app.get("releaseNotes"),
        "developer": app.get("artistName"),
        "developerId": app.get("artistId"),
        "developerUrl": app.get("artistViewUrl"),
        "seller": app.get("sellerName"),
        "sellerUrl": app.get("sellerUrl"),
        "genre": app.get("primaryGenreName"),
        "genres": app.get("genres", []),
        "genreIds": app.get("genreIds", []),
        "price": price,
        "free": price == 0,
        "currency": app.get("currency"),
        "formattedPrice": app.get("formattedPrice"),
        "score": app.get("averageUserRating"),
        "scoreCurrentVersion": app.get("averageUserRatingForCurrentVersion"),
        "ratings": app.get("userRatingCount"),
        "ratingsCurrentVersion": app.get("userRatingCountForCurrentVersion"),
        "version": app.get("version"),
        "released": app.get("releaseDate"),
        "updated": app.get("currentVersionReleaseDate"),
        "contentRating": app.get("contentAdvisoryRating") or app.get("trackContentRating"),
        "minimumOsVersion": app.get("minimumOsVersion"),
        "fileSizeBytes": app.get("fileSizeBytes"),
        "languages": app.get("languageCodesISO2A", []),
        "icon": app.get("artworkUrl512") or app.get("artworkUrl100"),
        "screenshots": app.get("screenshotUrls", []),
        "ipadScreenshots": app.get("ipadScreenshotUrls", []),
        "appletvScreenshots": app.get("appletvScreenshotUrls", []),
        "supportedDevices": app.get("supportedDevices", []),
        "advisories": app.get("advisories", []),
        "features": app.get("features", []),
        "url": app.get("trackViewUrl"),
        "country": country.lower(),
    }


def _extract_ios_version(operating_system: Optional[str]) -> Optional[str]:
    """pull "17.0" out of a string like "Requires iOS 17.0 or later" """
    if not operating_system:
        return None
    match = re.search(r"iOS[\s\u00a0]*([\d.]+)", operating_system)
    return match.group(1) if match else operating_system


def parse_app_metadata_from_page(response: ScrapeApiResponse, app_id: str, country: str) -> Dict:
    """fallback parser: read the ld+json block embedded in the apps.apple.com page.

    Used when the iTunes lookup API has no data for the app/country combo.
    Only a subset of fields (compared to parse_app_metadata) is available here.
    """
    script = response.selector.css('script#software-application[type="application/ld+json"]::text').get()
    data = json.loads(script) if script else {}
    if data.get("@type") != "SoftwareApplication" or not data.get("name"):
        raise ValueError(f"No app metadata found on apps.apple.com page for {app_id}")

    offers = data.get("offers") or {}
    rating = data.get("aggregateRating") or {}
    author = data.get("author") or {}
    price = offers.get("price") or 0
    genres = [genre for genre in (data.get("applicationCategory"), data.get("applicationSubCategory")) if genre]
    devices = [device.strip() for device in (data.get("availableOnDevice") or "").split(",") if device.strip()]

    return {
        "appId": str(app_id),
        "bundleId": None,
        "title": data.get("name"),
        "description": data.get("description"),
        "summary": None,
        "developer": author.get("name"),
        "developerId": None,
        "developerUrl": author.get("url"),
        "seller": author.get("name"),
        "sellerUrl": None,
        "genre": genres[0] if genres else None,
        "genres": genres,
        "genreIds": [],
        "price": price,
        "free": price == 0,
        "currency": offers.get("priceCurrency"),
        "formattedPrice": "Free" if price == 0 else None,
        "score": rating.get("ratingValue"),
        "scoreCurrentVersion": rating.get("ratingValue"),
        "ratings": rating.get("reviewCount"),
        "ratingsCurrentVersion": rating.get("reviewCount"),
        "version": None,
        "released": None,
        "updated": None,
        "contentRating": None,
        "minimumOsVersion": _extract_ios_version(data.get("operatingSystem")),
        "fileSizeBytes": None,
        "languages": [],
        "icon": data.get("image"),
        "screenshots": [],
        "ipadScreenshots": [],
        "appletvScreenshots": [],
        "supportedDevices": devices,
        "advisories": [],
        "features": [],
        "url": response.scrape_result.get("url") or response.config["url"],
        "country": country.lower(),
    }


def parse_reviews(response: ScrapeApiResponse) -> List[Dict]:
    """parse customer reviews from the iTunes RSS JSON feed"""
    data = json.loads(response.content)
    entries = data.get("feed", {}).get("entry") or []
    if isinstance(entries, dict):
        entries = [entries]

    reviews = []
    for entry in entries:
        if not entry.get("im:rating"):
            continue
        author = entry.get("author", {})
        link = entry.get("link", {}).get("attributes", {})
        reviews.append({
            "reviewId": _label(entry, "id"),
            "userName": author.get("name", {}).get("label"),
            "userUrl": author.get("uri", {}).get("label"),
            "title": _label(entry, "title"),
            "content": _label(entry, "content"),
            "score": int(_label(entry, "im:rating") or 0),
            "version": _label(entry, "im:version"),
            "voteSum": int(_label(entry, "im:voteSum") or 0),
            "voteCount": int(_label(entry, "im:voteCount") or 0),
            "updated": _label(entry, "updated"),
            "url": link.get("href"),
        })
    return reviews


async def scrape_app_metadata(app_id: str, country: str = "us") -> Dict:
    """scrape app metadata via the iTunes lookup API, falling back to the apps.apple.com page"""
    lookup_url = f"https://itunes.apple.com/lookup?id={app_id}&country={country}"
    response = await SCRAPFLY.async_scrape(ScrapeConfig(lookup_url, **BASE_CONFIG))

    try:
        metadata = parse_app_metadata(response, app_id, country)
    except:
        log.info("no iTunes data for {}, falling back to apps.apple.com", app_id)
        page_url = f"https://apps.apple.com/{country}/app/id{app_id}"
        response = await SCRAPFLY.async_scrape(ScrapeConfig(page_url, **BASE_CONFIG))
        metadata = parse_app_metadata_from_page(response, app_id, country)

    log.success("scraped metadata for {} ({})", metadata["title"], app_id)
    return metadata


async def scrape_reviews(app_id: str, country: str = "us", max_pages: int = None) -> List[Dict]:
    """scrape app reviews via the iTunes customer reviews RSS feed"""
    pages = min(max_pages or 10, 10)

    to_scrape = [
        ScrapeConfig(
            url=f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={app_id}/sortby=mostrecent/json",
            **BASE_CONFIG,
        )
        for page in range(1, pages + 1)
    ]

    reviews = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        reviews.extend(parse_reviews(response))

    log.success("scraped {} reviews for {}", len(reviews), app_id)
    return reviews
