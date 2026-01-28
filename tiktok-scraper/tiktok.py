"""
This is an example web scraper for TikTok.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import datetime
import secrets
import json
import uuid
import jmespath
from typing import Dict, List
from urllib.parse import urlencode, quote, urlparse, parse_qs
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass tiktok.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "AU",
}


def parse_post(response: ScrapeApiResponse) -> Dict:
    """parse hidden post data from HTML"""
    selector = response.selector
    data = selector.xpath("//script[@id='__UNIVERSAL_DATA_FOR_REHYDRATION__']/text()").get()
    post_data = json.loads(data)["__DEFAULT_SCOPE__"]["webapp.video-detail"]["itemInfo"]["itemStruct"]
    parsed_post_data = jmespath.search(
        """{
        id: id,
        desc: desc,
        createTime: createTime,
        video: video.{duration: duration, ratio: ratio, cover: cover, playAddr: playAddr, downloadAddr: downloadAddr, bitrate: bitrate},
        author: author.{id: id, uniqueId: uniqueId, nickname: nickname, avatarLarger: avatarLarger, signature: signature, verified: verified},
        stats: stats,
        locationCreated: locationCreated,
        diversificationLabels: diversificationLabels,
        suggestedWords: suggestedWords,
        contents: contents[].{textExtra: textExtra[].{hashtagName: hashtagName}}
        }""",
        post_data,
    )
    return parsed_post_data


async def scrape_posts(urls: List[str]) -> List[Dict]:
    """scrape tiktok posts data from their URLs"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG, render_js=True) for url in urls]
    data = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        post_data = parse_post(response)
        data.append(post_data)
    log.success(f"scraped {len(data)} posts from post pages")
    return data


def parse_comments(response: ScrapeApiResponse) -> List[Dict]:
    """parse comments data from the API response"""
    _xhr_calls = response.scrape_result["browser_data"]["xhr_call"]
    comment_call = [f for f in _xhr_calls if "/api/comment/list/" in f["url"]]
    for xhr in comment_call:
        if not xhr["response"]:
            continue
        data = json.loads(xhr["response"]["body"])
        break

    comments_data = data["comments"]
    parsed_comments = []
    # refine the comments with JMESPath
    for comment in comments_data:
        result = jmespath.search(
            """{
            text: text,
            comment_language: comment_language,
            digg_count: digg_count,
            reply_comment_total: reply_comment_total,
            author_pin: author_pin,
            create_time: create_time,
            cid: cid,
            nickname: user.nickname,
            unique_id: user.unique_id,
            aweme_id: aweme_id
            }""",
            comment,
        )
        parsed_comments.append(result)
    return parsed_comments


async def scrape_comments(post_url: str) -> List[Dict]:
    """scrape comments from tiktok posts from xhr call parsing"""
    log.info("scraping the post page for the comment data")
    response = await SCRAPFLY.async_scrape(ScrapeConfig(
        post_url, **BASE_CONFIG, render_js=True, rendering_wait=5000,
        # click the comment icon to load the comments and trigger the API call
        js_scenario=[
            {
                "wait_for_selector": {
                    "selector": "//span[@data-e2e='comment-icon']",
                    "timeout": 5000
                }
            },
            {
                "click": {
                    "ignore_if_not_visible": False,
                    "selector": "//span[@data-e2e='comment-icon']"
                }
            },
            {
                "wait_for_selector": {
                    "selector": "div.TUXTabBar",
                    "timeout": 5000
                }
            }
        ])
    )
    
    data = parse_comments(response)
    log.success(f"scraped {len(data)} comments from the post with the URL {post_url}")
    return data


def parse_profile(response: ScrapeApiResponse):
    """parse profile data from hidden scripts on the HTML"""
    selector = response.selector
    data = selector.xpath("//script[@id='__UNIVERSAL_DATA_FOR_REHYDRATION__']/text()").get()
    profile_data = json.loads(data)["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]
    return profile_data


async def scrape_profiles(urls: List[str]) -> List[Dict]:
    """scrape tiktok profiles data from their URLs"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG, render_js=True, wait_for_selector="#__UNIVERSAL_DATA_FOR_REHYDRATION__") for url in urls]
    data = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        profile_data = parse_profile(response)
        data.append(profile_data)
    log.success(f"scraped {len(data)} profiles from profile pages")
    return data


def parse_search(response: ScrapeApiResponse) -> List[Dict]:
    """parse search data from XHR calls"""
    # extract the xhr calls and extract the ones for search results
    _xhr_calls = response.scrape_result["browser_data"]["xhr_call"]
    search_calls = [c for c in _xhr_calls if "/api/search/general/full/" in c["url"]]
    search_data = []
    for search_call in search_calls:
        try:
            data = json.loads(search_call["response"]["body"])["data"]
        except Exception as e:
            log.error(f"Failed to parse search data from XHR call: {e}")
            continue
        search_data.extend(data)
    
    # parse all the data using jmespath
    parsed_search = []
    for item in search_data:
        if item["type"] == 1:  # get the item if it was item only
            result = jmespath.search(
                """{
                id: id,
                desc: desc,
                createTime: createTime,
                video: video,
                author: author,
                stats: stats,
                authorStats: authorStats
                }""",
                item["item"],
            )
            result["type"] = item["type"]
            parsed_search.append(result)
    return parsed_search


async def scrape_search(keyword: str) -> List[Dict]:
    """scrape tiktok search data by scrolling the search page"""
    # js code for scrolling down with maximum 15 scrolls. It stops at the end without using the full iterations
    js = """const scrollToEnd = (i = 0) => (window.innerHeight + window.scrollY >= document.body.scrollHeight || i >= 15) ? (console.log("Reached the bottom or maximum iterations. Stopping further iterations."), setTimeout(() => console.log("Waited 10 seconds after all iterations."), 10000)) : (window.scrollTo(0, document.body.scrollHeight), setTimeout(() => scrollToEnd(i + 1), 10000)); setTimeout(() => scrollToEnd(), 5000);"""
    url = f"https://www.tiktok.com/search?q={quote(keyword)}"
    log.info(f"scraping search page with the URL {url} for search data")
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url,
            asp=True,
            country="AU",
            wait_for_selector="//div[@data-e2e='search_top-item']",
            render_js=True,
            auto_scroll=True,
            rendering_wait=10000,
            js=js,
            debug=True,
        )
    )
    data = parse_search(response)
    log.success(f"scraped {len(data)} search results for keyword: {keyword}")
    return data


def parse_channel(response: ScrapeApiResponse):
    """parse channel video data from XHR calls"""
    # extract the xhr calls and extract the ones for videos
    _xhr_calls = response.scrape_result["browser_data"]["xhr_call"]
    post_calls = [c for c in _xhr_calls if "/api/post/item_list/" in c["url"]]
    channel_data = []
    for post_call in post_calls:
        try:
            data = json.loads(post_call["response"]["body"])["itemList"]
        except Exception:
            raise Exception("Post data couldn't load")
        channel_data.extend(data)
    # parse all the data using jmespath
    parsed_data = []
    for post in channel_data:
        result = jmespath.search(
            """{
            createTime: createTime,
            desc: desc,
            id: id,
            stats: stats,
            contents: contents[].{desc: desc, textExtra: textExtra[].{hashtagName: hashtagName}}
            }""",
            post,
        )
        parsed_data.append(result)
    return parsed_data


async def scrape_channel(url: str) -> List[Dict]:
    """scrape video data from a channel (profile with videos)"""
    # js code for scrolling down with maximum 15 scrolls. It stops at the end without using the full iterations
    js = """const scrollToEnd = (i = 0) => (window.innerHeight + window.scrollY >= document.body.scrollHeight || i >= 15) ? (console.log("Reached the bottom or maximum iterations. Stopping further iterations."), setTimeout(() => console.log("Waited 10 seconds after all iterations."), 10000)) : (window.scrollTo(0, document.body.scrollHeight), setTimeout(() => scrollToEnd(i + 1), 10000)); setTimeout(() => scrollToEnd(), 5000);"""
    log.info(f"scraping channel page with the URL {url} for post data")
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url,
            asp=True,
            country="AU",
            wait_for_selector="//div[@data-e2e='user-post-item-list']",
            render_js=True,
            auto_scroll=True,
            rendering_wait=10000,
            js=js,
            debug=True,
        )
    )
    data = parse_channel(response)
    log.success(f"scraped {len(data)} posts data")
    return data
