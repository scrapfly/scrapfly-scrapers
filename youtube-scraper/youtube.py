"""
This is an example web scraper for YouTube.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import datetime
import secrets
import json
import jmespath

from jsonpath_ng.ext import parse
from typing import Dict, List, Literal
from urllib.parse import urlencode, quote, urlparse, parse_qs
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # bypass youtube.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
}

jp_all = lambda query, data: [match.value for match in parse(query).find(data)]
jp_first = lambda query, data: (
    parse(query).find(data)[0].value if parse(query).find(data) else None
)


def convert_to_number(value):
    if value is None:
        return None

    value = value.strip().upper()

    if value.endswith("K"):
        return int(float(value[:-1]) * 1_000)

    elif value.endswith("M"):
        return int(float(value[:-1]) * 1_000_000)

    else:
        return int(float(value))


async def call_youtube_api(
    base_url: str,
    continuation_token: str = None,
    search_query: str = None,
    search_params: str = None,
) -> List[Dict]:
    """call the YouTube comments API for continuation or search queries"""
    payload = {
        "context": {
            "client": {
                "hl": "en",
                "gl": "US",
                "remoteHost": "",
                "deviceMake": "",
                "deviceModel": "",
                "visitorData": "",
                "userAgent": "",
                "clientName": "WEB",
                "clientVersion": "2.20241111.07.00",
                "osName": "",
                "osVersion": "",
                "originalUrl": "",
                "platform": "DESKTOP",
                "clientFormFactor": "UNKNOWN_FORM_FACTOR",
                "configInfo": {"appInstallData": ""},
                "userInterfaceTheme": "USER_INTERFACE_THEME_DARK",
                "timeZone": "",
                "browserName": "",
                "browserVersion": "",
                "acceptHeader": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "deviceExperimentId": "",
                "screenWidthPoints": None,
                "screenHeightPoints": None,
                "screenPixelDensity": None,
                "screenDensityFloat": None,
                "utcOffsetMinutes": None,
                "connectionType": "CONN_CELLULAR_4G",
                "memoryTotalKbytes": "8000000",
                "mainAppWebInfo": {
                    "graftUrl": "",
                    "pwaInstallabilityStatus": "PWA_INSTALLABILITY_STATUS_UNKNOWN",
                    "webDisplayMode": "WEB_DISPLAY_MODE_BROWSER",
                    "isWebNativeShareAvailable": True,
                },
            },
            "user": {"lockedSafetyMode": False},
            "request": {
                "useSsl": True,
                "internalExperimentFlags": [],
                "consistencyTokenJars": [],
            },
            "clickTracking": {"clickTrackingParams": ""},
        }
    }

    if search_query is not None:
        payload["query"] = search_query
        payload["params"] = search_params

    if continuation_token is not None:
        payload["continuation"] = continuation_token

    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            base_url,
            method="POST",
            body=json.dumps(payload),
            **BASE_CONFIG,
            headers={"content-type": "application/json"},
        )
    )
    return response


def parse_script_variable(script: str, variable: str) -> Dict:
    """parse the JSON object assigned to a JavaScript variable in a script tag"""
    if not script:
        raise ValueError(f"no script tag containing {variable} was found")
    _, separator, payload = script.partition(variable)
    if not separator:
        raise ValueError(f"{variable} was not found in the script tag")

    start = payload.find("{")
    if start == -1:
        raise ValueError(f"no JSON object was found after {variable}")

    return json.JSONDecoder().raw_decode(payload[start:])[0]


def parse_yt_initial_data(response: ScrapeApiResponse) -> Dict:
    """parse ytInitialData script from YouTube pages"""
    selector = response.selector
    data = selector.xpath("//script[contains(text(),'ytInitialData')]/text()").get()
    return parse_script_variable(data, "ytInitialData")


def parse_video_details(response: ScrapeApiResponse) -> Dict:
    """parse video metadata from YouTube video page"""
    selector = response.selector
    data = selector.xpath(
        "//script[contains(text(),'ytInitialPlayerResponse')]/text()"
    ).get()
    return parse_script_variable(data, "ytInitialPlayerResponse").get("videoDetails")


def parse_video(response: ScrapeApiResponse) -> Dict:
    """parse video metadata from YouTube video page"""
    video_details = parse_video_details(response)
    content_details = parse_yt_initial_data(response)

    likes = [
        i["title"]
        for i in jp_all("$..buttonViewModel", content_details)
        if "iconName" in i and i["iconName"] == "LIKE"
    ]
    channel_id = jp_first(
        "$..channelEndpoint.browseEndpoint.canonicalBaseUrl", content_details
    )
    verified = jp_all(
        "$..videoOwnerRenderer..badges[0].metadataBadgeRenderer", content_details
    )

    result = {
        "video": {
            "videoId": video_details.get("videoId"),
            "title": video_details.get("title"),
            "publishingDate": jp_first("$..dateText.simpleText", content_details),
            "lengthSeconds": convert_to_number(video_details.get("lengthSeconds")),
            "keywords": video_details.get("keywords"),
            "description": video_details.get("shortDescription"),
            "thumbnail": video_details.get("thumbnail").get("thumbnails"),
            "stats": {
                "viewCount": convert_to_number(video_details.get("viewCount")),
                "likeCount": convert_to_number(likes[0]) if likes else None,
                "commentCount": convert_to_number(
                    jp_first("$..contextualInfo.runs[0].text", content_details)
                ),
            },
        },
        "channel": {
            "name": video_details.get("author"),
            "identifierId": video_details.get("channelId"),
            "id": channel_id.replace("/", "") if channel_id else None,
            # channels can carry other badges instead ("Official Artist Channel")
            "verified": any(i.get("tooltip") == "Verified" for i in verified or []),
            "channelUrl": (
                f"https://www.youtube.com{channel_id}" if channel_id else None
            ),
            "subscriberCount": jp_first(
                "$..subscriberCountText.simpleText", content_details
            ),
            "thumbnails": jp_first(
                "$..engagementPanelSectionListRenderer..channelThumbnail.thumbnails",
                content_details,
            ),
        },
        "commentContinuationToken": jp_first(
            "$..continuationCommand.token", content_details
        ),
    }

    return result


async def scrape_video(ids: List[str]) -> List[Dict]:
    """scrape video metadata from YouTube videos"""
    data = []
    to_scrape = [
        ScrapeConfig(
            f"https://youtu.be/{video_id}",
            proxy_pool="public_residential_pool",
            **BASE_CONFIG,
            render_js=True,
            # the page is sometimes returned as an empty app shell, wait for the
            # video metadata to make sure the data scripts are rendered
            wait_for_selector="//ytd-watch-metadata",
        )
        for video_id in ids
    ]
    log.info(f"scraping {len(to_scrape)} video metadata from video pages")
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        post_data = parse_video(response)
        data.append(post_data)
    log.success(f"scraped {len(data)} video metadata from video pages")
    return data


def parse_comments_api(response: ScrapeApiResponse) -> List[Dict]:
    """parse comments API response for comment data"""
    parsed_comments = []
    data = json.loads(response.content)
    continuation_tokens = jp_all("$..continuationCommand.token", data)
    comments = jp_all("$..commentEntityPayload", data)
    for comment in comments:
        result = jmespath.search(
            """{
                comment: {
                    id: properties.commentId,
                    text: properties.content.content
                    publishedTime: properties.publishedTime
                },
                author: {
                    id: author.channelId,
                    displayName: author.displayName,
                    avatarThumbnail: author.avatarThumbnailUrl,
                    isVerified: author.isVerified,
                    isCurrentUser: author.isVerified,
                    isCreator: author.isVerified
                },
                stats: {
                    likeCount: toolbar.likeCountLiked,
                    replyCount: toolbar.replyCount
                }
            }""",
            comment,
        )
        parsed_comments.append(result)

    return {
        "comments": parsed_comments,
        "continuationToken": continuation_tokens[-1] if continuation_tokens else None,
    }


async def scrape_comments(video_id: str, max_scrape_pages=None) -> List[Dict]:
    """scraper comments from a YouTube video"""
    comments = []
    cursor = 0
    log.info(f"scraping video page for the comments continuation token")
    video_data = await scrape_video([video_id])
    continuation_token = video_data[0].get("commentContinuationToken")

    while continuation_token and (
        cursor < max_scrape_pages if max_scrape_pages else True
    ):
        cursor += 1
        log.info(f"scraping comments page with index {cursor}")
        response = await call_youtube_api(
            base_url="https://www.youtube.com/youtubei/v1/next?prettyPrint=false",
            continuation_token=continuation_token,
        )
        data = parse_comments_api(response)
        comments.extend(data["comments"])
        continuation_token = data["continuationToken"]

    log.success(f"scraped {len(comments)} comments for the video {video_id}")
    return comments


def parse_channel(response: ScrapeApiResponse) -> Dict:
    """parse channel metadata from YouTube channel page"""
    browser_data = response.scrape_result.get("browser_data") or {}
    _xhr_calls = browser_data.get("xhr_call") or []
    info_call = [c for c in _xhr_calls if "youtube.com/youtubei/v1/browse" in c["url"]]
    if not info_call:
        raise ValueError(
            "no browse API call was captured, the channel About panel didn't load"
        )
    data = json.loads(info_call[0]["response"]["body"])

    metadata = jp_first("$..aboutChannelViewModel", data)
    if not metadata:
        raise ValueError("no aboutChannelViewModel was found in the browse API response")

    links = []
    for i in metadata.get("links") or []:
        i = i["channelExternalLinkViewModel"]
        links.append(
            {
                "title": i["title"]["content"],
                "url": i["link"]["content"],
                "favicon": i["favicon"],
            }
        )
    result = jmespath.search(
        """{
        description: description,
        url: displayCanonicalChannelUrl,
        subscriberCount: subscriberCountText,
        videoCount: videoCountText,
        viewCount: viewCountText,
        joinedDate: joinedDateText.content,
        country: country
        }""",
        metadata,
    )
    result["links"] = links
    return result


async def scrape_channel(channel_ids: List[str]) -> List[Dict]:
    """scrape channel metadata from YouTube channel pages"""
    to_scrape = [
        ScrapeConfig(
            f"https://www.youtube.com/@{channel_id}",
            proxy_pool="public_residential_pool",
            **BASE_CONFIG,
            render_js=True,
            wait_for_selector="//yt-description-preview-view-model//button",
            js_scenario=[
                # click on the "show more" button to load the full description
                {
                    "click": {
                        "selector": "//yt-description-preview-view-model//button",
                        "ignore_if_not_visible": False,
                        "timeout": 10000,
                    }
                },
                {
                    "wait_for_selector": {
                        "selector": "//ytd-about-channel-renderer",
                        "timeout": 10000,
                    }
                },
            ],
        )
        for channel_id in channel_ids
    ]
    data = []
    log.info(f"scraping {len(to_scrape)} channels")
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        channel_data = parse_channel(response)
        data.append(channel_data)
    log.success(f"scraped {len(data)} cahnnel info")
    return data


def parse_video_items(items: List[Dict]) -> List[Dict]:
    """parse video data from the video grid items of channel pages and API responses"""
    parsed_videos = []
    for i in items or []:
        lockup = jp_first("$.richItemRenderer.content.lockupViewModel", i)
        if not lockup:
            continue
        result = jmespath.search(
            """{
            videoId: contentId,
            title: metadata.lockupMetadataViewModel.title.content,
            publishedTime: metadata.lockupMetadataViewModel.metadata.contentMetadataViewModel.metadataRows[0].metadataParts[1].text.content,
            viewCount: metadata.lockupMetadataViewModel.metadata.contentMetadataViewModel.metadataRows[0].metadataParts[0].text.content,
            lengthText: contentImage.thumbnailViewModel.overlays[0].thumbnailBottomOverlayViewModel.badges[0].thumbnailBadgeViewModel.text,
            thumbnails: contentImage.thumbnailViewModel.image.sources
            }""",
            lockup,
        )
        result["url"] = f"https://youtu.be/{result['videoId']}"
        parsed_videos.append(result)
    return parsed_videos


def parse_channel_videos_page(data: Dict) -> Dict:
    """parse the video grid rendered in the channel page HTML"""

    contents = jp_first("$..richGridRenderer.contents", data) or []
    return {
        "videos": parse_video_items(contents),
        "continuationToken": jp_first(
            "$..continuationItemRenderer..continuationCommand.token", contents
        ),
    }


def parse_video_api(response: ScrapeApiResponse) -> Dict:
    """parse video data from YouTube API response"""
    data = json.loads(response.content)
    continuation_tokens = jp_all("$..continuationCommand.token", data)

    videos = jp_all("$..reloadContinuationItemsCommand.continuationItems", data)
    videos = videos[-1] if len(videos) > 1 else jp_first("$..continuationItems", data)

    return {
        "videos": parse_video_items(videos),
        "continuationToken": continuation_tokens[-1] if continuation_tokens else None,
    }


async def scrape_channel_videos(
    channel_id: str,
    sort_by: Literal["Latest", "Popular", "Oldest"] = "Latest",
    max_scrape_pages: int = None,
) -> List[Dict]:
    """scrape video metadata from YouTube channel page"""
    # 1. extract the continuation token from the HTML to call the API
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            f"https://www.youtube.com/@{channel_id}/videos",
            proxy_pool="public_residential_pool",
            **BASE_CONFIG,
        )
    )
    initial_script_data = parse_yt_initial_data(response)
    chips = jp_all("$..chipViewModel", initial_script_data)

    # there are different continuation tokens based on the sorting order
    continuation_token = next(
        (
            jp_first("$.tapCommand..continuationCommand.token", i)
            for i in chips
            if i.get("text") == sort_by
        ),
        None,
    )

    videos = []
    cursor = 0

    # channels below a certain size don't render the sorting chips at all and
    # their videos are part of the channel page itself, already sorted by latest
    if not continuation_token:
        log.warning(
            f"no {sort_by} sorting chip found for the channel {channel_id}, "
            "falling back to the default video listing of the channel page"
        )
        data = parse_channel_videos_page(initial_script_data)
        videos.extend(data["videos"])
        continuation_token = data["continuationToken"]
        cursor += 1

    # 2. call the API to get the video data
    while continuation_token and (
        cursor < max_scrape_pages if max_scrape_pages else True
    ):
        cursor += 1
        log.info(f"scraping video page with index {cursor}")
        response = await call_youtube_api(
            base_url="https://www.youtube.com/youtubei/v1/browse?key=yt_web",
            continuation_token=continuation_token,
        )
        data = parse_video_api(response)
        videos.extend(data["videos"])
        continuation_token = data["continuationToken"]

    log.success(f"scraped {len(videos)} video for the channel {channel_id}")
    return videos


def parse_search_response(response: ScrapeApiResponse) -> List[Dict]:
    """parse search results from the YouTube API response"""
    results = []
    data = json.loads(response.content)
    search_boxes = jp_all("$..videoRenderer", data)
    for i in search_boxes:
        if "videoId" not in i:
            continue
        result = jmespath.search(
            """{
            id: videoId,
            title: title.runs[0].text,
            description: detailedMetadataSnippets[0].snippetText.runs[0].text,
            publishedTime: publishedTimeText.simpleText,
            videoLength: lengthText.simpleText,
            viewCount: viewCountText.simpleText,
            videoBadges: badges[].metadataBadgeRenderer.label,
            channelBadges: ownerBadges[].metadataBadgeRenderer.accessibilityData.label,
            viewCount: shortViewCountText.simpleText,
            videoThumbnails: thumbnail.thumbnails,
            channelThumbnails: channelThumbnailSupportedRenderers.channelThumbnailWithLinkRenderer.thumbnail.thumbnails
            }""",
            i,
        )
        result["url"] = f"https://youtu.be/{result['id']}"
        results.append(result)

    return {
        "videos": results,
        # scoped to the results list, the search filter chips in the header carry
        # their own tokens, which return pages without any search result
        "continuationToken": jp_first(
            "$..continuationItemRenderer..continuationCommand.token", data
        ),
    }


async def scrape_search(
    search_query: str, max_scrape_pages: int = None, search_params: str = None
) -> List[Dict]:
    """scrape search results from YouTube search query"""
    cursor = 0
    search_data = []
    response = await call_youtube_api(
        base_url="https://www.youtube.com/youtubei/v1/search?prettyPrint=false",
        search_query=search_query,
        search_params=search_params,
    )
    data = parse_search_response(response)
    search_data.extend(data["videos"])
    continuation_token = data["continuationToken"]

    while continuation_token and (
        cursor < max_scrape_pages if max_scrape_pages else True
    ):
        cursor += 1
        log.info(f"scraping search page with index {cursor}")
        response = await call_youtube_api(
            base_url="https://www.youtube.com/youtubei/v1/search?prettyPrint=false",
            continuation_token=continuation_token,  # use the continuation token after the first page
        )
        data = parse_search_response(response)
        search_data.extend(data["videos"])
        continuation_token = data["continuationToken"]

    log.success(f"scraped {len(search_data)} video for the query {search_query}")
    return search_data


async def scrape_shorts(ids: List[str]) -> List[Dict]:
    """scrape metadata from YouTube shorts"""
    to_scrape = [
        ScrapeConfig(
            f"https://youtu.be/{short_id}",
            proxy_pool="public_residential_pool",
            render_js=True,
            **BASE_CONFIG,
        )
        for short_id in ids
    ]
    data = []
    log.info(f"scraping {len(to_scrape)} short video metadata from video pages")
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        post_data = parse_video_details(response)
        post_data["thumbnail"] = post_data["thumbnail"]["thumbnails"]
        data.append(post_data)
    log.success(f"scraped {len(data)} video metadata from short pages")
    return data
