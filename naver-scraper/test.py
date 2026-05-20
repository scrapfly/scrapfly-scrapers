"""Test the naver scraper"""

import os
from cerberus import Validator as _Validator
import naver
import pytest
import pprint

pp = pprint.PrettyPrinter(indent=4)


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )


SEARCH_WEB_SCHEMA = {
    "title": {"type": "string", "required": True, "min_presence": 0.1},
    "url": {"type": "string", "required": True, "min_presence": 0.1},
    "snippet": {"type": "string", "required": True},
    "source": {"type": "string", "required": False, "nullable": True},
    "rank": {"type": "integer", "required": True},
}

SEARCH_IMAGE_SCHEMA = {
    "title": {"type": "string", "required": True},
    "link": {"type": "string", "required": True},
    "source": {"type": "string", "required": False, "nullable": True},
    "image_url": {"type": "string", "required": True},
    "thumbnail_url": {"type": "string", "required": True},
    "img_id": {"type": "string", "required": True},
    "color": {"type": "string", "required": True},
    "date": {"type": "string", "required": True},
    "writer": {"type": "string", "required": True},
    "domain": {"type": "string", "required": True},
    "rank": {"type": "integer", "required": True},
}

BLOG_POST_SCHEMA = {
    "url":      {"type": "string", "required": True},
    "title":    {"type": "string", "required": True, "min_presence": 0.1},
    "content":  {"type": "string", "required": True, "min_presence": 0.1},
    "author":   {"type": "string", "nullable": True, "min_presence": 0.1},
    "date":     {"type": "string", "nullable": True, "min_presence": 0.1},
    "images":   {"type": "list",   "required": True, "schema": {"type": "string"}, "min_presence": 0.1},
    "category": {"type": "string", "nullable": True, "min_presence": 0.1},
}

NEWS_ARTICLE_SCHEMA = {
    "url":          {"type": "string", "required": True},
    "title":        {"type": "string", "required": True, "min_presence": 0.1},
    "description":  {"type": "string", "nullable": True, "min_presence": 0.1},
    "content":      {"type": "string", "required": True, "min_presence": 0.1},
    "press":        {"type": "string", "nullable": True, "min_presence": 0.1},
    "date":         {"type": "string", "nullable": True, "min_presence": 0.1},
    "modified_date":{"type": "string", "nullable": True, "min_presence": 0.1},
    "images":       {"type": "list",   "required": True, "schema": {"type": "string"}, "min_presence": 0.1},
    "sections":     {"type": "list",   "required": True, "schema": {"type": "string"}, "min_presence": 0.1},
    "origin_url":   {"type": "string", "nullable": True, "min_presence": 0.1},
}

@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_web_search_scraping():
    results = await naver.scrape_web_search(query="파이썬", max_pages=3, period="6m")

    # Validate each search result
    result_validator = Validator(SEARCH_WEB_SCHEMA)
    for result in results["results"]:
        validate_or_fail(result, result_validator)

    for k in SEARCH_WEB_SCHEMA:
        require_min_presence(results["results"], k, min_perc=SEARCH_WEB_SCHEMA[k].get("min_presence", 0.1))

    assert len(results["results"]) >= 5

@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_image_search_scraping():
    results = await naver.scrape_image_search(query="파이썬", max_pages=3)

    # Validate each search result
    result_validator = Validator(SEARCH_IMAGE_SCHEMA)
    for result in results["results"]:
        validate_or_fail(result, result_validator)

    for k in SEARCH_IMAGE_SCHEMA:
        require_min_presence(results["results"], k, min_perc=SEARCH_IMAGE_SCHEMA[k].get("min_presence", 0.1))

    assert len(results["results"]) >= 20
    
@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_blog_post_scraping():
    results = await naver.scrape_blog_post([
        "https://blog.naver.com/cherry_27_/224290687381",
        "https://blog.naver.com/jylove_0120/224289170856",
        "https://blog.naver.com/oro-mam/224289142276"
    ])
    result_validator = Validator(BLOG_POST_SCHEMA)
    for result in results:
        validate_or_fail(result, result_validator)

    for k in BLOG_POST_SCHEMA:
        require_min_presence(results, k, min_perc=BLOG_POST_SCHEMA[k].get("min_presence", 0.1))


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_news_article_scraping():
    results = await naver.scrape_news_article([
        "https://n.news.naver.com/article/001/0015234567",
        "https://n.news.naver.com/article/001/0015234568",
        "https://n.news.naver.com/article/001/0015234569",
    ])
    result_validator = Validator(NEWS_ARTICLE_SCHEMA)
    for result in results:
        validate_or_fail(result, result_validator)

    for k in NEWS_ARTICLE_SCHEMA:
        require_min_presence(results, k, min_perc=NEWS_ARTICLE_SCHEMA[k].get("min_presence", 0.1))
