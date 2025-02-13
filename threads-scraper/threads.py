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

from nested_lookup import nested_lookup
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Threads.net might require Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "country": "US",  # set country here NOTE: Threads is not available in Europe yet
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
        reply_count: post.text_post_app_info.direct_reply_count,
        like_count: post.like_count,
        images: post.carousel_media[].image_versions2.candidates[1].url,
        image_count: post.carousel_media_count,
        videos: post.video_versions[].url
    }""",
        data,
    )
    result["videos"] = list(set(result["videos"] or []))
    result["url"] = f"https://www.threads.net/@{result['username']}/post/{result['code']}"
    result['image_count'] = len(result.get('images') or "")  # backwards compatibility with old dataset
    return result


def parse_profile(data: Dict) -> Dict:
    """Parse Threads profile JSON dataset for the most important fields"""
    result = jmespath.search(
        """{
        is_private: text_post_app_is_private,
        is_verified: is_verified,
        profile_pic: hd_profile_pic_versions[-1].url,
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
    log.info("scraping thread: {}", url)
    for _ in range(3):
        result = await SCRAPFLY.async_scrape(
            ScrapeConfig(url, **BASE_CONFIG)
        )
        if '/accounts/login' not in result.context['url']:
            break
    else:
        raise Exception('encountered endless login requirement redirect loop - does the post exist?')

    if 'error=invalid_post' in result.context['url']:
        log.debug('post not found or deleted: {}', url)
        return {}

    hidden_datasets = result.selector.css('script[type="application/json"][data-sjs]::text').getall()
    for hidden_dataset in hidden_datasets:
        # skip loading datasets that clearly don't contain threads data
        if '"ScheduledServerJS"' not in hidden_dataset:
            continue
        if 'thread_items' not in hidden_dataset:
            continue
        data = json.loads(hidden_dataset)        
        thread_items = nested_lookup('thread_items', data)
        if not thread_items:
            continue
        threads = [
            parse_thread(t) for thread in thread_items for t in thread
        ]
        return {
            "thread": threads[0],
            "replies": threads[1:],
        }
    raise ValueError('could not find thread data in page')


async def scrape_profile(url: str) -> Dict:
    """
    Scrapes Twitter user profile page e.g.:
    https://www.threads.net/@zuck
    returns user data and latest tweets
    """
    log.info("scraping profile: {}", url)
    for _ in range(3):
        result = await SCRAPFLY.async_scrape(
            ScrapeConfig(url, auto_scroll=True, **BASE_CONFIG)
        )
        if '/accounts/login' not in result.context['url']:
            break
    else:
        raise Exception('encountered endless login requirement redirect loop - does the profile exist?')
    parsed = {
        "user": {},
        "threads": [],
    }
    # find all hidden datasets
    hidden_datasets = result.selector.css('script[type="application/json"][data-sjs]::text').getall()
    for hidden_dataset in hidden_datasets:
        # skip loading datasets that clearly don't contain threads data
        if '"ScheduledServerJS"' not in hidden_dataset:
            continue
        is_profile = 'follower_count' in hidden_dataset
        is_threads = 'thread_items' in hidden_dataset
        if not is_profile and not is_threads:
            continue
        data = json.loads(hidden_dataset)
        if is_profile:
            user_data = nested_lookup('user', data)
            parsed['user'] = parse_profile(user_data[0])
        if is_threads:
            thread_items = nested_lookup('thread_items', data)
            threads = [
                parse_thread(t) for thread in thread_items for t in thread
            ]
            parsed['threads'].extend(threads)
    return parsed
