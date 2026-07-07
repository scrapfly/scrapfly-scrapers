"""
This is an example web scraper for capterra.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import re
from typing import Dict, List, Optional, TypedDict
from urllib.parse import urljoin

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    "asp": True,
    "render_js": True,
    "country": "US",
    "proxy_pool": "public_residential_pool",
}


class CategoryProduct(TypedDict):
    product_id: str
    name: str
    url: str
    reviews_url: str
    logo: Optional[str]
    rating: Optional[float]
    review_count: Optional[int]
    rating_breakdown: Dict[str, Optional[float]]
    description: Optional[str]
    features: List[str]


def parse_category_page(response: ScrapeApiResponse) -> List[CategoryProduct]:
    """Parse product listings from a Capterra category page."""
    sel = response.selector
    base_url = "https://www.capterra.com"
    products = []

    for card in sel.css('[data-testid^="product-card-container-"]'):
        product_id_match = re.search(
            r"product-card-container-(\d+)",
            card.css("::attr(data-testid)").get(""),
        )
        if not product_id_match:
            continue

        name = card.css('[data-testid^="product-header-"]::text').get()
        if not name:
            continue

        relative_url = card.css(
            'a[data-trk-label="text-link_learn-more"]::attr(href)'
        ).get() or card.css('a[href*="/p/"]::attr(href)').get()
        if not relative_url:
            continue

        url = urljoin(base_url, relative_url)
        reviews_path = card.css('a[href*="/reviews/"]::attr(href)').get()
        reviews_url = urljoin(base_url, reviews_path) if reviews_path else url.rstrip("/") + "/reviews/"

        rating = review_count = None
        review_text = card.css('a[href*="/reviews/"]').xpath("string(.)").get()
        if review_text:
            m = re.search(r"^([\d.]+)", review_text.strip())
            if m:
                rating = float(m.group(1))
            m = re.search(r"\(([\d,]+)\)", review_text)
            if m:
                review_count = int(m.group(1).replace(",", ""))

        card_text = " ".join(t.strip() for t in card.css("::text").getall() if t.strip())
        rating_breakdown = {}
        for label, key in [
            ("Overall", "overall"),
            ("Ease of Use", "ease_of_use"),
            ("Customer Service", "customer_service"),
            ("Features", "features"),
            ("Value for Money", "value_for_money"),
        ]:
            m = re.search(rf"{re.escape(label)}\s+([\d.]+)", card_text)
            rating_breakdown[key] = float(m.group(1)) if m else None

        description = None
        for p in card.css("p"):
            text = "".join(p.css("::text").getall()).strip()
            if text and "features reviewers most value" not in text:
                description = text.split("Learn more about")[0].strip()
                break

        features = [
            t.strip()
            for t in card.css('[data-testid="product-card-category-features"] .flex.items-center::text').getall()
            if t.strip()
        ]

        products.append({
            "product_id": product_id_match.group(1),
            "name": name.strip(),
            "url": url,
            "reviews_url": reviews_url,
            "logo": card.css("img::attr(src)").get(),
            "rating": rating,
            "review_count": review_count,
            "rating_breakdown": rating_breakdown,
            "description": description,
            "features": features,
        })

    return products


def _get_total_pages(response: ScrapeApiResponse) -> int:
    pages = [
        int(re.search(r"page=(\d+)", href).group(1))
        for href in response.selector.css(
            '[data-testid="pagination-section"] a[href*="page="]::attr(href)'
        ).getall()
        if re.search(r"page=(\d+)", href)
    ]
    return max(pages) if pages else 1


async def scrape_category(category: str, max_pages: int = None) -> List[CategoryProduct]:
    """Scrape category listings with pagination."""
    base_url = f"https://www.capterra.com/{category}/"
    log.info(f"scraping category page {base_url}")

    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(base_url, **BASE_CONFIG))
    products = parse_category_page(first_page)
    total_pages = _get_total_pages(first_page)

    if max_pages and max_pages < total_pages:
        total_pages = max_pages

    if total_pages > 1:
        log.info(f"scraping category pagination, remaining ({total_pages - 1}) more pages")
        to_scrape = [
            ScrapeConfig(f"{base_url}?page={page}", **BASE_CONFIG)
            for page in range(2, total_pages + 1)
        ]
        async for response in SCRAPFLY.concurrent_scrape(to_scrape):
            try:
                products.extend(parse_category_page(response))
            except Exception as exc:
                log.error(f"failed to parse page: {exc}")

    log.success(f"scraped {len(products)} products from Capterra category '{category}'")
    return products


def parse_review_page(response: ScrapeApiResponse) -> Dict:
    """Parse product review page."""
    pass


async def scrape_reviews(url: str, max_review_pages: int = None) -> List[Dict]:
    """Scrape product reviews."""
    pass
