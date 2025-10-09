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


async def retrieve_comment_params(post_url: str, session: str) -> Dict:
    """retrieve query parameters for the comments API"""
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            post_url,
            **BASE_CONFIG,
            render_js=True,
            rendering_wait=5000,
            session=session,
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
    session_id = uuid.uuid4().hex  # generate a random session ID for the comments API
    api_params = await retrieve_comment_params(post_url, session_id)

    def form_api_url(cursor: int):
        """form the reviews API URL and its pagination values"""
        base_url = "https://www.tiktok.com/api/comment/list/?"
        params = {"count": comments_count, "cursor": cursor, **api_params}  # the index to start from
        return base_url + urlencode(params)
    
    log.info("scraping the first comments batch")
    first_page = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            form_api_url(cursor=0), **BASE_CONFIG,
            headers={"content-type": "application/json"},
            render_js=True, session=session_id
        )
    )
    data = parse_comments(first_page)
    comments_data = data["comments"]
    total_comments = data["total_comments"]

    # get the maximum number of comments to scrape
    if max_comments and max_comments < total_comments:
        total_comments = max_comments

    # scrape the remaining comments concurrently
    _other_pages = [
        ScrapeConfig(
            form_api_url(cursor=cursor), **BASE_CONFIG,
            headers={"content-type": "application/json"},
            session=session_id, render_js=True
        )
        for cursor in range(comments_count, total_comments + comments_count, comments_count)
    ]
    
    for scrape_config in _other_pages:
        response = await SCRAPFLY.async_scrape(scrape_config)
        try:
            data = parse_comments(response)["comments"]
        except Exception as e:
            log.error(f"error scraping comments: {e}")
            continue
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
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG, render_js=True, wait_for_selector="#__UNIVERSAL_DATA_FOR_REHYDRATION__") for url in urls]
    data = []
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        profile_data = parse_profile(response)
        data.append(profile_data)
    log.success(f"scraped {len(data)} profiles from profile pages")
    return data


def parse_search(response: ScrapeApiResponse) -> List[Dict]:
    """parse search data from the API response"""
    try:
        data = json.loads(response.scrape_result["content"])
        search_data = data["data"]
    except Exception as e:
        log.error(f"Failed to parse JSON from search API response: {e}")
        return None

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
    session_id = str(uuid.uuid4().hex)
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
        if data is not None:
            search_data.extend(data)

    log.success(f"scraped {len(search_data)} from the search API from the keyword {keyword}")
    return search_data


def parse_channel(videos: List[Dict]) -> List[Dict]:
    """parse video data from API response"""
    parsed_data = []
    for post in videos:
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

async def scrape_channel(url: str, max_pages: int = 5, max_videos_per_request: int = 18) -> List[Dict]:
    """scrape video data from a channel by calling the item_list API directly
        Args:
            url (str): The channel URL to scrape.
            max_pages (int, optional): Maximum number of pages to fetch. Defaults to 5.
            max_videos_per_request (int, optional): Number of videos to request per API call. 
                recommend to be within (10, 20). Some channels may fail if this value is set higher.
    """
    
    # First, get the user's secUid from their profile page
    log.info(f"fetching profile to extract secUid from {url}")
    profile_response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url,
            **BASE_CONFIG,
            render_js=True,
            rendering_wait=3000,
        )
    )
    
    _xhr_calls = profile_response.scrape_result["browser_data"]["xhr_call"]
    log.info(f"found {len(_xhr_calls)} XHR calls")
    
    sec_uid = None
    aid = None
    
    for xhr in _xhr_calls:
        if "/api/post/item_list/" in xhr.get("url", ""):
            log.info(f"found item_list XHR call: {xhr.get('url')[:100]}...")
            # Parse the URL to extract query parameters
            parsed_url = urlparse(xhr["url"])
            query_params = parse_qs(parsed_url.query)
            
            # Extract just the aid and sec_uid
            aid = query_params.get("aid", [None])[0]
            sec_uid = query_params.get("secUid", [None])[0]  # Fixed: was missing [0]

            log.info(f"extracted API parameters: aid={aid}, secUid={sec_uid[:20] if sec_uid else None}...")
            break
    
    # Failback 
    if not aid or not sec_uid:
        log.warning("Could not extract aid or secUid from XHR calls, using fallback method")
        # Extract secUid from the profile page data
        selector = profile_response.selector
        script_data = selector.xpath("//script[@id='__UNIVERSAL_DATA_FOR_REHYDRATION__']/text()").get()
        if script_data:
            user_data = json.loads(script_data)["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]
            sec_uid = user_data["user"]["secUid"]
            log.info(f"extracted secUid from page data: {sec_uid[:20]}...")
        else:
            raise Exception("Could not extract secUid from page data")
            
        # Use default params for aid if we can't extract them
        if not aid:
            aid = "1988"
            log.warning(f"using default aid: {aid}")
    
    def build_api_url(cursor: int = 0) -> str:
        """Build the item_list API URL with proper parameters"""
        # These parameters are based on what TikTok's web app uses
        params = {
            "aid": aid,
            "count": max_videos_per_request,
            "cursor": cursor,
            "secUid": sec_uid,
            "root_referer": url,
        }
        return f"https://www.tiktok.com/api/post/item_list/?{urlencode(params)}"
    
    # Fetch videos using pagination
    all_videos = []
    cursor = 0
    has_more = True
    current_page = 0
    
    # Create a session to maintain cookies
    session_id = session_id = str(uuid.uuid4().hex)
    log.info(f"starting video fetch loop, max_pages={max_pages}")

    while has_more and current_page < max_pages:
        log.info(f"fetching videos batch, page: {current_page + 1}/{max_pages}, cursor: {cursor}, current total: {len(all_videos)}")
        
        api_response = await SCRAPFLY.async_scrape(
            ScrapeConfig(
                build_api_url(cursor),
                **BASE_CONFIG,
                headers={"content-type": "application/json"},
                session=session_id,
            )
        )
        
        try:
            data = json.loads(api_response.scrape_result["content"])
        except Exception as e:
            log.error(f"failed to parse API response: {e}")
            break
        
        if data.get("itemList"):
            videos = data["itemList"]
            all_videos.extend(videos)
            log.info(f"fetched {len(videos)} videos, total: {len(all_videos)}")
            
            # Update cursor for next page
            has_more = data.get("hasMore", False)
            cursor = data.get("cursor", 0)
            current_page += 1
            log.debug(f"hasMore={has_more}, next cursor={cursor}, current_page={current_page}")
        else:
            log.warning("no videos found in response, stopping pagination")
            break
    
    log.info(f"parsing {len(all_videos)} videos")
    # Parse the video data
    data = parse_channel(all_videos)

    log.success(f"scraped {len(data)} videos from channel")
    return data