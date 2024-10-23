"""
This is an example web scraper for TikTok.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import datetime
import secrets
import json
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
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    data = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        post_data = parse_post(response)
        data.append(post_data)
    log.success(f"scraped {len(data)} posts from post pages")
    return data


def parse_comments(response: ScrapeApiResponse) -> List[Dict]:
    """parse comments data from the API response"""
    data = json.loads(response.scrape_result["content"])
    comments_data = data["comments"]
    total_comments = data["total"]
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
    return {"comments": parsed_comments, "total_comments": total_comments}


async def retrieve_comment_params(post_url: str) -> Dict:
    """retrieve query parameters for the comments API"""
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            post_url,
            **BASE_CONFIG,
            render_js=True,
            rendering_wait=5000,
            wait_for_selector="//a[@data-e2e='comment-avatar-1']",
        )
    )

    _xhr_calls = response.scrape_result["browser_data"]["xhr_call"]
    for i in _xhr_calls:
        if "api/comment/list" not in i["url"]:
            continue
        url = urlparse(i["url"])
        qs = parse_qs(url.query)
        # remove the params we'll override
        for key in ["count", "cursor"]:
            _ = qs.pop(key, None)
        api_params = {key: value[0] for key, value in qs.items()}
        return api_params


async def scrape_comments(post_url: str, comments_count: int = 20, max_comments: int = None) -> List[Dict]:
    """scrape comments from tiktok posts using hidden APIs"""
    post_id = post_url.split("/video/")[1].split("?")[0]
    api_params = await retrieve_comment_params(post_url)

    def form_api_url(cursor: int):
        """form the reviews API URL and its pagination values"""
        base_url = "https://www.tiktok.com/api/comment/list/?"
        params = {"count": comments_count, "cursor": cursor, **api_params}  # the index to start from
        return base_url + urlencode(params)

    log.info("scraping the first comments batch")
    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(form_api_url(cursor=0), **BASE_CONFIG, headers={"content-type": "application/json"})
    )
    data = parse_comments(first_page)
    comments_data = data["comments"]
    total_comments = data["total_comments"]

    # get the maximum number of comments to scrape
    if max_comments and max_comments < total_comments:
        total_comments = max_comments

    # scrape the remaining comments concurrently
    log.info(f"scraping comments pagination, remaining {total_comments // comments_count - 1} more pages")
    _other_pages = [
        ScrapeConfig(form_api_url(cursor=cursor), **BASE_CONFIG, headers={"content-type": "application/json"})
        for cursor in range(comments_count, total_comments + comments_count, comments_count)
    ]
    async for response in SCRAPFLY.concurrent_scrape(_other_pages):
        data = parse_comments(response)["comments"]
        comments_data.extend(data)

    log.success(f"scraped {len(comments_data)} from the comments API from the post with the ID {post_id}")
    return comments_data


def parse_profile(response: ScrapeApiResponse):
    """parse profile data from hidden scripts on the HTML"""
    selector = response.selector
    data = selector.xpath("//script[@id='__UNIVERSAL_DATA_FOR_REHYDRATION__']/text()").get()
    profile_data = json.loads(data)["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]
    return profile_data


async def scrape_profiles(urls: List[str]) -> List[Dict]:
    """scrape tiktok profiles data from their URLs"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG, render_js=True) for url in urls]
    data = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        profile_data = parse_profile(response)
        data.append(profile_data)
    log.success(f"scraped {len(data)} profiles from profile pages")
    return data


def parse_search(response: ScrapeApiResponse) -> List[Dict]:
    """parse search data from the API response"""
    data = json.loads(response.scrape_result["content"])
    search_data = data["data"]
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

    # wheter there is more search results: 0 or 1. There is no max searches available
    has_more = data["has_more"]
    return parsed_search


async def obtain_session(url: str) -> str:
    """create a session to save the cookies and authorize the search API"""
    session_id = "tiktok_search_session"
    await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG, render_js=True, session=session_id))
    return session_id


async def scrape_search(keyword: str, max_search: int, search_count: int = 12) -> List[Dict]:
    """scrape tiktok search data from the search API"""

    def generate_search_id():
        # get the current datetime and format it as YYYYMMDDHHMMSS
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        # calculate the length of the random hex required for the total length (32)
        random_hex_length = (32 - len(timestamp)) // 2  # calculate bytes needed
        random_hex = secrets.token_hex(random_hex_length).upper()
        random_id = timestamp + random_hex
        return random_id

    def form_api_url(cursor: int):
        """form the reviews API URL and its pagination values"""
        base_url = "https://www.tiktok.com/api/search/general/full/?"
        params = {
            "keyword": quote(keyword),
            "offset": cursor,  # the index to start from
            "search_id": generate_search_id(),
        }
        return base_url + urlencode(params)

    log.info("obtaining a session for the search API")
    session_id = await obtain_session(url="https://www.tiktok.com/search?q=" + quote(keyword))

    log.info("scraping the first search batch")
    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            form_api_url(cursor=0),
            **BASE_CONFIG,
            headers={
                "content-type": "application/json",
            },
            session=session_id,
        )
    )
    search_data = parse_search(first_page)

    # scrape the remaining comments concurrently
    log.info(f"scraping search pagination, remaining {max_search // search_count} more pages")
    _other_pages = [
        ScrapeConfig(
            form_api_url(cursor=cursor), **BASE_CONFIG, headers={"content-type": "application/json"}, session=session_id
        )
        for cursor in range(search_count, max_search + search_count, search_count)
    ]
    async for response in SCRAPFLY.concurrent_scrape(_other_pages):
        data = parse_search(response)
        search_data.extend(data)

    log.success(f"scraped {len(search_data)} from the search API from the keyword {keyword}")
    return search_data


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
    js = """const scrollToEnd = (i = 0) => (window.innerHeight + window.scrollY >= document.body.scrollHeight || i >= 15) ? (console.log("Reached the bottom or maximum iterations. Stopping further iterations."), setTimeout(() => console.log("Waited 10 seconds after all iterations."), 10000)) : (window.scrollTo(0, document.body.scrollHeight), setTimeout(() => scrollToEnd(i + 1), 5000)); scrollToEnd();"""
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
