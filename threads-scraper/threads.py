"""
This is an example web scraper for Threads.net used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-threads/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
import re
from urllib.parse import urlencode

import jmespath

from typing import Dict, List, Optional, Tuple

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
THREADS_APP_ID = "238260118697367"  # ssr_qpl_app_id embedded in every page
MAX_REPLY_PAGES = 3  # extra reply screens to fetch, each is another API call


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
    for key in ("id", "pk", "user_pk", "user_id"):  # ids can come back as ints
        if result.get(key) is not None:
            result[key] = str(result[key])
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


def _reply_posts(info: Dict) -> Tuple[List[Dict], Dict]:
    """Flatten one direct_replies connection into (posts, page_info)"""
    replies = (info or {}).get("direct_replies") or {}
    posts = []
    for edge in replies.get("edges") or []:
        for post_edge in ((edge.get("node") or {}).get("posts") or {}).get("edges") or []:
            post = (post_edge or {}).get("node") or {}
            if post.get("code"):
                posts.append(post)
    return posts, replies.get("page_info") or {}


def _thread_data(result, code: str) -> Tuple[Optional[Dict], List[Dict], Dict, Optional[Dict]]:
    """Find the root post, its first reply screen, and the reply pagination query in the page's hidden JSON"""
    root = None
    reply_posts: List[Dict] = []
    page_info: Dict = {}
    query = None
    for raw in result.selector.css('script[type="application/json"][data-sjs]::text').getall():
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for media in nested_lookup("media", payload):
            if not isinstance(media, dict):
                continue
            if root is None and media.get("code") == code:
                root = media
            if not reply_posts:
                reply_posts, page_info = _reply_posts(media.get("text_post_app_info"))
        if query is None:
            for preloaders in nested_lookup("expectedPreloaders", payload):
                for entry in preloaders or []:
                    if entry.get("queryName") == "BarcelonaPostPageDownwardQuery":
                        query = entry
    return root, reply_posts, page_info, query


async def _scrape_more_replies(
    session: str, referer: str, lsd: str, query: Dict, page_info: Dict, seen_codes: set
) -> List[Dict]:
    """Follow direct_replies.page_info.end_cursor with the same query the page used"""
    posts: List[Dict] = []
    variables = dict(query["variables"])
    pages = 1
    while page_info.get("has_next_page") and page_info.get("end_cursor") and pages < MAX_REPLY_PAGES:
        variables["after"] = page_info["end_cursor"]
        variables["first"] = 10
        body = urlencode({
            "lsd": lsd,
            "doc_id": str(query["queryID"]),
            "variables": json.dumps(variables, separators=(",", ":")),
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "BarcelonaPostPageDownwardQuery",
            "server_timestamps": "true",
            "av": "0",
            "__user": "0",
            "__a": "1",
        })
        result = await SCRAPFLY.async_scrape(ScrapeConfig(
            "https://www.threads.com/api/graphql",
            method="POST",
            body=body,
            headers={
                "content-type": "application/x-www-form-urlencoded",
                "x-ig-app-id": THREADS_APP_ID,
                "x-fb-lsd": lsd,
                "x-fb-friendly-name": "BarcelonaPostPageDownwardQuery",
                "origin": "https://www.threads.com",
                "referer": referer,
            },
            session=session,
            **BASE_CONFIG,
        ))
        try:
            data = json.loads(result.content)
        except json.JSONDecodeError:
            log.warning("reply pagination returned non-json for {}", referer)
            break
        if data.get("errors"):
            log.warning("reply pagination error: {}", data["errors"])
            break
        media = (data.get("data") or {}).get("media") or {}
        new_posts, page_info = _reply_posts(media.get("text_post_app_info") or {})
        fresh = [post for post in new_posts if post.get("code") not in seen_codes]
        if not fresh:
            break
        for post in fresh:
            seen_codes.add(post["code"])
        posts.extend(fresh)
        pages += 1
    return posts


async def scrape_thread(url: str) -> Dict:
    """
    Scrape a single thread page: 
    https://www.threads.net/t/CuVdfsNtmvh/
    Return parent thread and reply threads
    """
    log.info("scraping thread: {}", url)
    path = [part for part in url.split("?")[0].rstrip("/").split("/") if part]
    code = path[path.index("post") + 1] if "post" in path else path[-1]
    session = f"threads-post-{code}"  # reused by reply pagination calls below
    for _ in range(3):
        result = await SCRAPFLY.async_scrape(
            ScrapeConfig(url, session=session, **BASE_CONFIG)
        )
        if '/accounts/login' not in result.context['url']:
            break
    else:
        raise Exception('encountered endless login requirement redirect loop - does the post exist?')

    if 'error=invalid_post' in result.context['url']:
        log.debug('post not found or deleted: {}', url)
        return {}

    root, reply_posts, page_info, query = _thread_data(result, code)
    if not root:
        raise ValueError(f'could not find thread data in page: {url}')

    seen_codes = {root.get("code")} | {post.get("code") for post in reply_posts}
    lsd_match = re.search(r'\["LSD",\[\],\{"token":"([^"]+)"\}', result.content)
    if query and lsd_match and page_info.get("has_next_page"):
        lsd = lsd_match.group(1)
        referer = result.context.get("url") or url
        reply_posts.extend(
            await _scrape_more_replies(session, referer, lsd, query, page_info, seen_codes)
        )

    threads = [parse_thread({"post": root})]
    threads.extend(parse_thread({"post": post}) for post in reply_posts)
    return {
        "thread": threads[0],
        "replies": threads[1:],
    }


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
