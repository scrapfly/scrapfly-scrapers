"""
This is an example web scraper for Goodreads.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

from loguru import logger as log
from parsel import Selector
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # goodreads.com requires Anti Scraping Protection bypass feature.
    "asp": True,
}


def _to_int(value: Optional[str]) -> Optional[int]:
    """convert a string like '6,103,353' to an int, stripping non-digit characters"""
    if not value:
        return None
    digits = re.sub(r"[^\d]", "", value)
    return int(digits) if digits else None


def _find_book_ld_json(sel: Selector) -> Dict:
    """find the Book JSON-LD block embedded in the page"""
    for script in sel.xpath('//script[@type="application/ld+json"]/text()').getall():
        try:
            data = json.loads(script)
        except json.JSONDecodeError:
            continue
        if data.get("@type") == "Book":
            return data
    return {}


def parse_book(response: ScrapeApiResponse) -> Dict:
    """parse book page and return book data"""
    sel = response.selector
    ld = _find_book_ld_json(sel)
    rating = ld.get("aggregateRating") or {}
    authors = ld.get("author") or []

    description = " ".join(
        t.strip() for t in sel.css('div[data-testid="description"] .Formatted::text').getall() if t.strip()
    )
    genres = [
        g.strip()
        for g in sel.css(
            'div[data-testid="genresList"] span.BookPageMetadataSection__genreButton a '
            "span.Button__labelItem::text"
        ).getall()
        if g.strip()
    ]
    awards = [a.strip() for a in (ld.get("awards") or "").split(",") if a.strip()]

    return {
        "url": sel.xpath('//link[@rel="canonical"]/@href').get(),
        "title": sel.css('h1[data-testid="bookTitle"]::text').get() or ld.get("name"),
        "author": {
            "name": authors[0].get("name") if authors else None,
            "url": authors[0].get("url") if authors else None,
        },
        "description": description or None,
        "image_url": ld.get("image") or sel.xpath('//meta[@property="og:image"]/@content').get(),
        "genres": genres or None,
        "num_pages": ld.get("numberOfPages"),
        "format": ld.get("bookFormat"),
        "language": ld.get("inLanguage"),
        "isbn": ld.get("isbn"),
        "awards": awards or None,
        "first_published": sel.css('p[data-testid="publicationInfo"]::text').get(),
        "rating": {
            "average": rating.get("ratingValue"),
            "ratings_count": rating.get("ratingCount"),
            "reviews_count": rating.get("reviewCount"),
        },
    }


def parse_list(response: ScrapeApiResponse) -> List[Dict]:
    """parse a list page and return book stubs (title, url, author, rating, etc.) found on it"""
    sel = response.selector
    books = []
    for row in sel.css("tr[itemtype='http://schema.org/Book']"):
        row_html = row.get()
        rating_text = row.css("span.minirating::text").get() or ""
        rating_m = re.search(r"([\d.]+)\s*avg rating", rating_text)
        ratings_m = re.search(r"([\d,]+)\s*ratings", rating_text)
        score_m = re.search(r"score:\s*([\d,]+)", row_html)
        votes_m = re.search(r"([\d,]+)\s*people voted", row_html)
        book_path = row.css("a.bookTitle::attr(href)").get()

        books.append(
            {
                "rank": _to_int(row.css("td.number::text").get()),
                "title": row.css("a.bookTitle span[itemprop='name']::text").get(),
                "url": urljoin("https://www.goodreads.com", book_path) if book_path else None,
                "author": row.css("span[itemprop='author'] span[itemprop='name']::text").get(),
                "author_url": row.css("a.authorName::attr(href)").get(),
                "image_url": row.css("img.bookCover::attr(src)").get(),
                "avg_rating": float(rating_m.group(1)) if rating_m else None,
                "ratings_count": _to_int(ratings_m.group(1)) if ratings_m else None,
                "score": _to_int(score_m.group(1)) if score_m else None,
                "votes": _to_int(votes_m.group(1)) if votes_m else None,
            }
        )
    log.success(f"parsed {len(books)} books from the list")
    return books


async def scrape_book(url: str) -> Dict:
    """scrape a single book page and return parsed book data"""
    log.info("scraping book {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    return parse_book(result)


async def scrape_list(url: str, enrich: bool = False) -> List[Dict]:
    """
    scrape a book list page and return book stubs found on it.
    if enrich=True, additionally scrape each book's page for full details.
    """
    log.info("scraping list {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    stubs = parse_list(result)

    if not enrich:
        return stubs

    books = []
    for stub in stubs:
        book_url = stub.get("url")
        if not book_url:
            continue
        books.append(await scrape_book(book_url))
    return books
