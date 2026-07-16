"""
This is an example web scraper for IMDb.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import html
import json
import os
import re
from typing import Dict, List, Optional, TypedDict
from urllib.parse import quote_plus

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "proxy_pool": "public_residential_pool",
    "render_js": True,
    "rendering_wait": 5000,
}


class IMDbReview(TypedDict):
    id: str
    author: Optional[str]
    summary: Optional[str]
    text: Optional[str]
    rating: Optional[int]
    spoiler: bool


class IMDbTitle(TypedDict):
    id: str
    url: str
    name: str
    type: Optional[str]
    rating_value: Optional[float]
    rating_count: Optional[int]
    content_rating: Optional[str]
    genre: Optional[List[str]]
    description: Optional[str]
    cast: Optional[List[Dict]]
    directors: Optional[List[Dict]]
    runtime_minutes: Optional[int]
    keywords: Optional[List[str]]
    box_office: Optional[Dict]
    release_date: Optional[str]


class IMDbSearchResult(TypedDict):
    id: str
    url: str
    name: Optional[str]
    type: Optional[str]
    year: Optional[int]
    rating_value: Optional[float]
    rating_count: Optional[int]


class IMDbChartEntry(TypedDict):
    rank: Optional[int]
    id: str
    url: str
    name: Optional[str]
    type: Optional[str]
    rating_value: Optional[float]
    rating_count: Optional[int]
    year: Optional[int]


class IMDbPerson(TypedDict):
    id: Optional[str]
    url: str
    name: Optional[str]
    bio: Optional[str]
    birth_date: Optional[str]
    professions: Optional[List[str]]
    filmography: Optional[List[Dict]]


def _parse_next_data(sel) -> Dict:
    """parse full __NEXT_DATA__ JSON from a page selector"""
    raw = sel.css("script#__NEXT_DATA__::text").get()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _parse_ld_json(sel, types: Optional[tuple] = None) -> Dict:
    """parse application/ld+json from a page selector"""
    for script in sel.css('script[type="application/ld+json"]::text'):
        try:
            data = json.loads(script.get() or "{}")
        except json.JSONDecodeError:
            continue
        if not types or data.get("@type") in types:
            return data
    return {}


def _parse_money(node: Optional[Dict]) -> Optional[Dict]:
    """normalize IMDb money nodes ({total: ...} or {budget: ...})"""
    if not node:
        return None
    return node.get("total") or node.get("budget")


def parse_title(response: ScrapeApiResponse) -> IMDbTitle:
    """parse title metadata from ld+json (box office from __NEXT_DATA__)"""
    sel = response.selector
    ld = _parse_ld_json(sel, ("Movie", "TVSeries", "TVEpisode", "TVMovie", "TVMiniSeries", "VideoGame"))
    page = _parse_next_data(sel).get("props", {}).get("pageProps", {})
    main = page.get("mainColumnData") or {}
    rating = ld.get("aggregateRating") or {}
    runtime = ((page.get("aboveTheFoldData") or {}).get("runtime") or {}).get("seconds")

    return IMDbTitle(
        id=ld["url"].rstrip("/").split("/")[-1],
        url=ld["url"],
        name=ld["name"],
        type=ld["@type"],
        rating_value=rating.get("ratingValue"),
        rating_count=rating.get("ratingCount"),
        content_rating=ld.get("contentRating"),
        genre=ld.get("genre"),
        description=ld.get("description"),
        cast=ld.get("actor"),
        directors=ld.get("director"),
        runtime_minutes=runtime // 60 if runtime else None,
        keywords=ld.get("keywords", "").split(","),
        box_office={
            "budget": _parse_money(main.get("productionBudget")),
            "gross_us_canada": _parse_money(main.get("lifetimeGross")),
            "gross_worldwide": _parse_money(main.get("worldwideGross")),
            "opening_weekend": _parse_money((main.get("openingWeekendGross") or {}).get("gross")),
        },
        release_date=ld.get("datePublished"),
    )


async def scrape_titles(urls: List[str]) -> List[IMDbTitle]:
    """scrape IMDb title pages for metadata and aggregate ratings"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    titles = []
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            log.info("scraping title {}", result.context["url"])
            titles.append(parse_title(result))
        except Exception as e:
            log.error(f"failed to scrape title: {e}")
    log.success(f"scraped {len(titles)} titles")
    return titles


def parse_reviews(response: ScrapeApiResponse) -> List[IMDbReview]:
    """parse user reviews from /reviews/ page __NEXT_DATA__"""
    page = _parse_next_data(response.selector).get("props", {}).get("pageProps", {})
    items = ((page.get("contentData") or {}).get("reviews")) or []
    reviews = []
    for item in items:
        review = item.get("review") or {}
        author = review.get("author") or {}
        raw = review.get("reviewText") or ""
        text = html.unescape(raw)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
        text = re.sub(r"<[^>]+>", "", text).strip() or None
        reviews.append(
            IMDbReview(
                id=review.get("reviewId"),
                author=(author.get("username") or {}).get("text"),
                summary=review.get("reviewSummary"),
                text=text,
                rating=review.get("authorRating"),
                spoiler=bool(review.get("spoiler")),
            )
        )
    return reviews


async def scrape_reviews(title_id: str) -> List[IMDbReview]:
    """scrape user reviews from IMDb /reviews/ pages"""
    url = f"https://www.imdb.com/title/{title_id}/reviews/"
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    reviews = []
    reviews = parse_reviews(result)
    log.success(f"scraped {len(reviews)} reviews for {title_id}")
    return reviews


def parse_search(response: ScrapeApiResponse) -> List[IMDbSearchResult]:
    """parse IMDb title search results from __NEXT_DATA__"""
    page = _parse_next_data(response.selector).get("props", {}).get("pageProps", {})
    results = []
    for entry in (page.get("titleResults") or {}).get("results", []):
        item = entry.get("listItem") or {}
        title_id = item.get("titleId")
        if not title_id:
            continue
        rating = item.get("ratingSummary") or {}
        results.append(
            IMDbSearchResult(
                id=title_id,
                url=f"https://www.imdb.com/title/{title_id}/",
                name=item.get("titleText"),
                type=(item.get("titleType") or {}).get("id"),
                year=item.get("releaseYear"),
                rating_value=rating.get("aggregateRating"),
                rating_count=rating.get("voteCount"),
            )
        )
    return results


async def scrape_search(query: str) -> List[IMDbSearchResult]:
    """scrape IMDb title search results for a query"""
    url = f"https://www.imdb.com/find/?q={quote_plus(query)}&s=tt"
    log.info(f"scraping search {url}")
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    results = parse_search(result)
    log.success(f"scraped {len(results)} search results for query '{query}'")
    return results


def parse_chart(response: ScrapeApiResponse) -> List[IMDbChartEntry]:
    """parse IMDb chart entries from __NEXT_DATA__"""
    page = _parse_next_data(response.selector).get("props", {}).get("pageProps", {})
    edges = ((page.get("pageData") or {}).get("chartTitles") or {}).get("edges") or []
    entries = []
    for edge in edges:
        node = edge.get("node") or {}
        title_id = node.get("id")
        if not title_id:
            continue
        rating = node.get("ratingsSummary") or {}
        entries.append(
            IMDbChartEntry(
                rank=edge.get("currentRank"),
                id=title_id,
                url=f"https://www.imdb.com/title/{title_id}/",
                name=(node.get("titleText") or {}).get("text"),
                type=(node.get("titleType") or {}).get("id"),
                rating_value=rating.get("aggregateRating"),
                rating_count=rating.get("voteCount"),
                year=(node.get("releaseYear") or {}).get("year"),
            )
        )
    return entries


async def scrape_chart(chart_type: str = "top") -> List[IMDbChartEntry]:
    """scrape an IMDb chart (e.g. 'top' for Top 250)"""
    url = f"https://www.imdb.com/chart/{chart_type}/"
    log.info(f"scraping chart {url}")
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    entries = parse_chart(result)
    log.success(f"scraped {len(entries)} entries from the {chart_type} chart")
    return entries


def parse_person(response: ScrapeApiResponse) -> IMDbPerson:
    """parse IMDb person biography and filmography from __NEXT_DATA__"""
    page = _parse_next_data(response.selector).get("props", {}).get("pageProps", {})
    above = page.get("aboveTheFold") or {}
    main = page.get("mainColumnData") or {}

    filmography = []
    for group in (main.get("released") or {}).get("edges") or []:
        node = group.get("node") or {}
        category = (node.get("grouping") or {}).get("text")
        for credit in (node.get("credits") or {}).get("edges", []):
            title = (credit.get("node") or {}).get("title") or {}
            if not title.get("id"):
                continue
            filmography.append(
                {
                    "id": title["id"],
                    "name": (title.get("titleText") or {}).get("text"),
                    "type": (title.get("titleType") or {}).get("text"),
                    "category": category,
                }
            )

    return IMDbPerson(
        id=page.get("nmconst"),
        url=response.context["url"],
        name=(above.get("nameText") or {}).get("text"),
        bio=((above.get("bio") or {}).get("text") or {}).get("plainText"),
        birth_date=(above.get("birthDate") or {}).get("date"),
        professions=[
            p["category"]["text"]
            for p in above.get("primaryProfessions") or []
            if (p.get("category") or {}).get("text")
        ] or None,
        filmography=filmography or None,
    )


async def scrape_person(person_id: str) -> IMDbPerson:
    """scrape an IMDb person page for biography and filmography"""
    url = f"https://www.imdb.com/name/{person_id}/"
    log.info(f"scraping person {url}")
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    person = parse_person(result)
    log.success(f"scraped person {person_id}")
    return person
