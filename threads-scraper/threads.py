"""
This is an example web scraper for Threads.net used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-threads/

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
    # Threads.net might require Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    # Threads.net is javascript-powered web application so it requires
    # headless browsers for scraping
    "render_js": True,
    "country": "US",  # set country here NOTE: Threads is not available in Europe
}


def parse_thread(data: Dict) -> Dict:
    """Parse Twitter tweet JSON dataset for the most important fields"""
    result = jmespath.search(
        """{
        text: post.caption.text,
        published_on: post.taken_at,
        id: post.id,
        pk: post.pk,
        code: post.code,
        username: post.user.username,
        user_pic: post.user.profile_pic_url,
        user_verified: post.user.is_verified,
        user_pk: post.user.pk,
        user_id: post.user.id,
        has_audio: post.has_audio,
        reply_count: view_replies_cta_string,
        like_count: post.like_count,
        images: post.carousel_media[].image_versions2.candidates[1].url,
        image_count: post.carousel_media_count,
        videos: post.video_versions[].url
    }""",
        data,
    )
    result["videos"] = list(set(result["videos"] or []))
    if result["reply_count"]:
        result["reply_count"] = int(result["reply_count"].split(" ")[0])
    result["url"] = f"https://www.threads.net/@{result['username']}/post/{result['code']}"
    return result


def parse_profile(data: Dict) -> Dict:
    """Parse Threads profile JSON dataset for the most important fields"""
    result = jmespath.search(
        """{
        is_private: is_private,
        is_verified: is_verified,
        profile_pic: profile_pic_url,
        username: username,
        full_name: full_name,
        bio: biography,
        bio_links: bio_links[].url,
        followers: follower_count
    }""",
        data,
    )
    result["url"] = f"https://www.threads.net/@{result['username']}"
    return result



async def scrape_thread(url: str) -> Dict:
    """
    Scrape a single thread page: 
    https://www.threads.net/t/CuVdfsNtmvh/
    Return parent thread and reply threads
    """
    for _ in range(3):
        result = await SCRAPFLY.async_scrape(
            ScrapeConfig(url, auto_scroll=True, **BASE_CONFIG)
        )
        if '/accounts/login' not in result.context['url']:
            break
    else:
        raise Exception('encountered endless login requirement redirect loop - does the post exist?')
    # capture background requests and extract ones that contain user data
    # and their latest tweets
    _xhr_calls = result.scrape_result["browser_data"]["xhr_call"]
    gql_calls = [f for f in _xhr_calls if "/api/graphql" in f["url"]]
    parsed = {
        "thread": {},
        "replies": [],
    }
    for xhr in gql_calls:
        data = json.loads(xhr["response"]["body"])
        try:
            parsed['thread'] = parse_thread(data['data']['data']['containing_thread']['thread_items'][0])
        except KeyError:
            log.warning("unknown graphql call type {}", xhr['body'])
            continue
        for reply in data['data']['data']['reply_threads']:
            parsed['replies'].extend([
                parse_thread(t)
                for t in reply['thread_items']
            ])
    return parsed


async def scrape_profile(url: str) -> Dict:
    """
    Scrapes Twitter user profile page e.g.:
    https://www.threads.net/@zuck
    returns user data and latest tweets
    """
    for _ in range(3):
        result = await SCRAPFLY.async_scrape(
            ScrapeConfig(url, auto_scroll=True, **BASE_CONFIG)
        )
        if '/accounts/login' not in result.context['url']:
            break
    else:
        raise Exception('encountered endless login requirement redirect loop - does the profile exist?')
    # capture background requests and extract ones that contain user data
    # and their latest tweets
    _xhr_calls = result.scrape_result["browser_data"]["xhr_call"]
    gql_calls = [f for f in _xhr_calls if "/api/graphql" in f["url"]]
    parsed = {
        "user": None,
        "threads": [],
    }
    for xhr in gql_calls:
        data = json.loads(xhr["response"]["body"])
        if data["data"].get("userData"):
            parsed['user'] = parse_profile(data["data"]["userData"]["user"])
        elif data["data"].get("mediaData"):
            for thread in data["data"]["mediaData"]["threads"]:
                parsed["threads"].extend([parse_thread(t) for t in thread['thread_items']])
        else:
            log.warning("unknown graphql call type {}", xhr['body'])
    return parsed
