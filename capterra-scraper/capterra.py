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


class ReviewRatings(TypedDict):
    overall: Optional[float]
    ease_of_use: Optional[float]
    features: Optional[float]
    value_for_money: Optional[float]
    customer_service: Optional[float]
    likelihood_to_recommend: Optional[int]


class Review(TypedDict):
    title: str
    date: Optional[str]
    reviewer_name: str
    reviewer_role: Optional[str]
    reviewer_industry: Optional[str]
    reviewer_usage_duration: Optional[str]
    reviewer_avatar: Optional[str]
    ratings: ReviewRatings
    review_body: Optional[str]
    pros: Optional[str]
    cons: Optional[str]


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


def _get_total_pages(response: ScrapeApiResponse, href_selector: str) -> int:
    hrefs = " ".join(response.selector.css(href_selector).getall())
    pages = [int(n) for n in re.findall(r"page=(\d+)", hrefs)]
    return max(pages, default=1)


async def scrape_category(category: str, max_pages: int = None) -> List[CategoryProduct]:
    """Scrape category listings with pagination."""
    base_url = f"https://www.capterra.com/{category}/"
    log.info(f"scraping category page {base_url}")

    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(base_url, **BASE_CONFIG))
    products = parse_category_page(first_page)
    total_pages = _get_total_pages(
        first_page,
        '[data-testid="pagination-section"] a[href*="page="]::attr(href)',
    )

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


def _parse_rating_value(card, testid: str) -> Optional[float]:
    """Extract the numeric rating value for a given data-testid rating element."""
    text = card.css(f'[data-testid="{testid}"] span:nth-child(2)::text').get()
    if text:
        try:
            return float(text.strip())
        except ValueError:
            pass
    return None


def parse_review_page(response: ScrapeApiResponse) -> List[Review]:
    """Parse product reviews from a Capterra review page."""
    sel = response.selector
    reviews = []

    for card in sel.css("div[data-test-id='review-cards-container'] > div > div"):
        reviewer_texts = [
            t.strip()
            for t in card.xpath(
                './/div[contains(@class,"text-neutral-90") and contains(@class,"w-full")]//text()'
            ).getall()
            if t.strip()
        ]

        name = reviewer_texts[0] if reviewer_texts else ""
        role = reviewer_texts[1] if len(reviewer_texts) > 1 else None
        industry = reviewer_texts[2] if len(reviewer_texts) > 2 else None

        usage_duration = None
        for i, text in enumerate(reviewer_texts):
            if "used the software for" in text.lower() and i + 1 < len(reviewer_texts):
                usage_duration = reviewer_texts[i + 1]
                # industry may appear before the usage marker, so stop after match
                if industry and "used the software for" in industry.lower():
                    industry = reviewer_texts[2] if len(reviewer_texts) > 2 else None
                break

        avatar = card.css('img[data-testid="reviewer-profile-pic"]::attr(src)').get()

        title = card.css("h3.font-semibold::text").get("").strip()
        date = card.css(".typo-0.text-neutral-90::text").get()

        likelihood_raw = card.css('progress[max="10"]::attr(value)').get()
        likelihood = int(likelihood_raw) if likelihood_raw else None

        ratings: ReviewRatings = {
            "overall": _parse_rating_value(card, "Overall Rating-rating"),
            "ease_of_use": _parse_rating_value(card, "Ease of Use-rating"),
            "features": _parse_rating_value(card, "Features-rating"),
            "value_for_money": _parse_rating_value(card, "Value for Money-rating"),
            "customer_service": _parse_rating_value(card, "Customer Service-rating"),
            "likelihood_to_recommend": likelihood,
        }

        review_body = card.xpath(
            './/div[contains(@class,"!mt-4")]//p[1]'
        ).xpath("string(.)").get()

        pros = cons = None
        for section in card.css(".space-y-2"):
            icon_title = section.css("title::text").get()
            if icon_title == "Positive icon":
                pros = section.css("p").xpath("string(.)").get()
            elif icon_title == "Negative icon":
                cons = section.css("p").xpath("string(.)").get()

        reviews.append(
            Review(
                title=title,
                date=date.strip() if date else None,
                reviewer_name=name,
                reviewer_role=role,
                reviewer_industry=industry,
                reviewer_usage_duration=usage_duration,
                reviewer_avatar=avatar,
                ratings=ratings,
                review_body=review_body.strip() if review_body else None,
                pros=pros.strip() if pros else None,
                cons=cons.strip() if cons else None,
            )
        )

    return reviews


async def scrape_reviews(url: str, max_review_pages: int = None) -> List[Review]:
    """Scrape paginated product reviews."""
    url = url.rstrip("/")
    if not url.endswith("/reviews"):
        url += "/reviews"
    url += "/"

    log.info(f"scraping reviews from {url}")
    first_page = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    reviews = parse_review_page(first_page)
    total_pages = _get_total_pages(first_page, '[data-testid="page-item-section"]::attr(href)')

    if max_review_pages and max_review_pages < total_pages:
        total_pages = max_review_pages

    if total_pages > 1:
        log.info(f"scraping reviews pagination, remaining ({total_pages - 1}) more pages")
        to_scrape = [
            ScrapeConfig(f"{url}?page={page}", **BASE_CONFIG)
            for page in range(2, total_pages + 1)
        ]
        async for response in SCRAPFLY.concurrent_scrape(to_scrape):
            try:
                reviews.extend(parse_review_page(response))
            except Exception as exc:
                log.error(f"failed to parse reviews page: {exc}")

    log.success(f"scraped {len(reviews)} reviews from {url}")
    return reviews
