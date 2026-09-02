"""
This is an example web scraper for Goodreads.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from urllib.parse import parse_qsl, quote_plus, urlencode, urljoin, urlparse, urlunparse

from loguru import logger as log
from parsel import Selector
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # goodreads.com requires Anti Scraping Protection bypass feature.
    "asp": True,
}

# Goodreads timestamps are epoch milliseconds, and go negative for pre 1970 publications
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _to_int(value: Optional[str]) -> Optional[int]:
    """convert a string like '6,103,353' to an int, stripping non-digit characters"""
    if not value:
        return None
    digits = re.sub(r"[^\d]", "", value)
    return int(digits) if digits else None


def _clean_url(href: Optional[str]) -> Optional[str]:
    """absolutize a Goodreads href and drop its tracking query

    Search result links carry from_search, qid and rank parameters that belong to one search
    response, so keeping them would make the same book look like a different URL.
    """
    if not href:
        return None
    return urljoin("https://www.goodreads.com", urlparse(href)._replace(query="", fragment="").geturl())


def _plain_text(html: Optional[str]) -> Optional[str]:
    """flatten a Goodreads review body, which arrives as an HTML fragment, into plain text"""
    if not html:
        return None
    return " ".join(Selector(text=html).xpath("string()").get("").split()) or None


def _iso(epoch_ms: Optional[int]) -> Optional[str]:
    """convert a Goodreads epoch milliseconds timestamp to an ISO date string"""
    if not isinstance(epoch_ms, int):
        return None
    return (EPOCH + timedelta(milliseconds=epoch_ms)).isoformat()


def _apollo(response: ScrapeApiResponse) -> Dict:
    """parse the normalized Apollo cache out of __NEXT_DATA__

    Goodreads exposes no standalone __APOLLO_STATE__ global, the cache only reaches the page
    through the Next.js payload, so a missing payload means the Apollo layer is unavailable.
    """
    raw = response.selector.css("script#__NEXT_DATA__::text").get()
    if not raw:
        log.warning("no __NEXT_DATA__ on {}", response.context["url"])
        return {}
    return json.loads(raw).get("props", {}).get("pageProps", {}).get("apolloState", {}) or {}


def _resolve(apollo: Dict, node) -> Dict:
    """follow an Apollo __ref pointer to the record it names"""
    if isinstance(node, dict) and "__ref" in node:
        return apollo.get(node["__ref"]) or {}
    return node if isinstance(node, dict) else {}


def _page_url(url: str, page: int) -> str:
    """set the page query parameter of a Goodreads search URL"""
    parts = urlparse(url)
    query = [(key, value) for key, value in parse_qsl(parts.query) if key != "page"] + [("page", str(page))]
    return urlunparse(parts._replace(query=urlencode(query)))


def _total_pages(response: ScrapeApiResponse) -> int:
    """read the last page number out of the plain link list Goodreads paginates with"""
    pages = [int(text) for text in response.selector.css('a[href*="page="]::text').getall() if text.strip().isdigit()]
    return max(pages) if pages else 1


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
            'div[data-testid="genresList"] span.BookPageMetadataSection__genreButton a ' "span.Button__labelItem::text"
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
                "url": _clean_url(book_path),
                "author": row.css("span[itemprop='author'] span[itemprop='name']::text").get(),
                "author_url": _clean_url(row.css("a.authorName::attr(href)").get()),
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


def parse_reviews(response: ScrapeApiResponse) -> List[Dict]:
    """parse the review sample of a book page from its Apollo Review records

    Reviews are resolved through the getReviews root query, so every review belongs to the
    requested book and each reviewer stays attached to their own review. The page ships a
    sample of the reviews rather than all of them: the review URL exposes no working
    pagination parameter, and the real total is reported as getReviews.totalCount.
    """
    apollo = _apollo(response)
    connection = (apollo.get("ROOT_QUERY") or {}).get("getReviews") or {}
    reviews = []
    for edge in connection.get("edges") or []:
        review = _resolve(apollo, edge.get("node"))
        if not review.get("id"):
            continue
        creator = _resolve(apollo, review.get("creator"))
        reviews.append(
            {
                "review_id": review["id"],
                "reviewer": creator.get("name"),
                "reviewer_url": creator.get("webUrl"),
                # a text review left without stars is reported as 0, which is not a rating
                "rating": review.get("rating") or None,
                "text": _plain_text(review.get("text")),
                "created_at": _iso(review.get("createdAt")),
                "updated_at": _iso(review.get("updatedAt")),
                "likes": review.get("likeCount"),
                "comments": review.get("commentCount"),
                "spoiler": review.get("spoilerStatus"),
            }
        )
    log.success(f"parsed {len(reviews)} reviews of {connection.get('totalCount')} total")
    return reviews


async def scrape_reviews(url: str) -> List[Dict]:
    """scrape the review sample a Goodreads book page ships with"""
    log.info("scraping reviews of {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    return parse_reviews(result)


async def scrape_search(query: str, max_pages: int = 2) -> List[Dict]:
    """scrape book stubs from Goodreads search results

    Search results are rendered with the same table markup as list pages, so the rows are
    read by parse_list. Rank, score and votes are list page columns and stay None here.
    """
    base_url = f"https://www.goodreads.com/search?q={quote_plus(query)}"

    log.info(f"scraping the first search page for '{query}'")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(base_url, **BASE_CONFIG))
    books = parse_list(first_page)
    total_pages = min(_total_pages(first_page), max_pages)

    log.info(f"scraping search pagination, remaining ({total_pages - 1}) more pages")
    to_scrape = [ScrapeConfig(_page_url(base_url, page), **BASE_CONFIG) for page in range(2, total_pages + 1)]
    async for result in SCRAPFLY.concurrent_scrape(to_scrape):
        if not isinstance(result, ScrapeApiResponse):
            continue
        try:
            books.extend(parse_list(result))
        except Exception as e:
            log.error(f"failed to scrape search page: {e}")

    # the same book can show up on more than one search page
    unique = list({book["url"]: book for book in books if book.get("url")}.values())
    log.success(f"scraped {len(unique)} books from search")
    return unique
