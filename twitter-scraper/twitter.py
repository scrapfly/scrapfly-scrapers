"""
This is an example web scraper for Twitter.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-twitter/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
import jmespath

from typing import Dict

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # X.com (Twitter) requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    # X.com (Twitter) is javascript-powered web application so it requires
    # headless browsers for scraping
    "render_js": True,
}


async def _scrape_twitter_app(url: str, _retries: int = 0, **scrape_config) -> Dict:
    """Scrape X.com (Twitter) page and scroll to the end of the page if possible"""
    if not _retries:
        log.info("scraping {}", url)
    else:
        log.info("retrying {}/2 {}", _retries, url)
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, auto_scroll=True, lang=["en-US"], **scrape_config, **BASE_CONFIG)
    )
    if "Something went wrong, but" in result.content:
        if _retries > 2:
            raise Exception("Twitter web app crashed too many times")
        return await _scrape_twitter_app(url, _retries=_retries + 1, **scrape_config)
    return result


def parse_tweet(data: Dict) -> Dict:
    """Parse X.com (Twitter) tweet JSON dataset for the most important fields"""
    result = jmespath.search(
        """{
        created_at: legacy.created_at,
        attached_urls: legacy.entities.urls[].expanded_url,
        attached_urls2: legacy.entities.url.urls[].expanded_url,
        attached_media: legacy.entities.media[].media_url_https,
        tagged_users: legacy.entities.user_mentions[].screen_name,
        tagged_hashtags: legacy.entities.hashtags[].text,
        favorite_count: legacy.favorite_count,
        bookmark_count: legacy.bookmark_count,
        quote_count: legacy.quote_count,
        reply_count: legacy.reply_count,
        retweet_count: legacy.retweet_count,
        quote_count: legacy.quote_count,
        text: legacy.full_text,
        is_quote: legacy.is_quote_status,
        is_retweet: legacy.retweeted,
        language: legacy.lang,
        user_id: legacy.user_id_str,
        id: legacy.id_str,
        conversation_id: legacy.conversation_id_str,
        source: source,
        views: views.count
    }""",
        data,
    )
    result["poll"] = {}
    poll_data = jmespath.search("card.legacy.binding_values", data) or []
    for poll_entry in poll_data:
        key, value = poll_entry["key"], poll_entry["value"]
        if "choice" in key:
            result["poll"][key] = value["string_value"]
        elif "end_datetime" in key:
            result["poll"]["end"] = value["string_value"]
        elif "last_updated_datetime" in key:
            result["poll"]["updated"] = value["string_value"]
        elif "counts_are_final" in key:
            result["poll"]["ended"] = value["boolean_value"]
        elif "duration_minutes" in key:
            result["poll"]["duration"] = value["string_value"]
    user_data = jmespath.search("core.user_results.result", data)
    if user_data:
        result["user"] = parse_profile(user_data)
    return result


async def scrape_tweet(url: str) -> Dict:
    """
    Scrape a single tweet page for Tweet thread e.g.:
    https://twitter.com/Scrapfly_dev/status/1667013143904567296
    Return parent tweet, reply tweets and recommended tweets
    """
    result = await _scrape_twitter_app(url, wait_for_selector="[data-testid='tweet']")
    # capture background requests and extract ones that request Tweet data
    _xhr_calls = result.scrape_result["browser_data"]["xhr_call"]
    tweet_call = [f for f in _xhr_calls if "TweetResultByRestId" in f["url"]]
    for xhr in tweet_call:
        if not xhr["response"]:
            continue
        data = json.loads(xhr["response"]["body"])
        return parse_tweet(data['data']['tweetResult']['result'])


def parse_profile(data: Dict) -> Dict:
    """parse X.com (Twitter) user profile JSON dataset as a flat structure"""
    return {"id": data["id"], "rest_id": data["rest_id"], "verified": data["is_blue_verified"], **data["legacy"]}


async def scrape_profile(url: str) -> Dict:
    """
    Scrapes X.com (Twitter) user profile page e.g.:
    https://x.com/scrapfly_dev
    returns user data and latest tweets
    """
    result = await _scrape_twitter_app(url, wait_for_selector="[data-testid='primaryColumn']")
    # capture background requests and extract ones that contain user data
    # and their latest tweets
    _xhr_calls = result.scrape_result["browser_data"]["xhr_call"]
    user_calls = [f for f in _xhr_calls if "UserBy" in f["url"]]
    for xhr in user_calls:
        data = json.loads(xhr["response"]["body"])
        parsed = parse_profile(data["data"]["user"]["result"])
        return parsed
    raise Exception("Failed to scrape user profile - no matching user data background requests")
