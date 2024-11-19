from cerberus import Validator
import pytest

import youtube
import pprint

pp = pprint.PrettyPrinter(indent=2)


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


_thumnails_schema = {
    "type": "list",
    "schema": {
        "type": "dict",
        "schema": {
            "url": {"type": "string"},
            "width": {"type": "integer"},
            "height": {"type": "integer"},
        },
    },
}

channel_videos_schema = {
    "videoId": {"type": "string"},
    "title": {"type": "string"},
    "description": {"type": "string"},
    "publishedTime": {"type": "string"},
    "lengthText": {"type": "string"},
    "viewCount": {"type": "string"},
    "thumbnails": _thumnails_schema,
    "url": {"type": "string"},
}

channel_schema = {
    "description": {"type": "string"},
    "url": {"type": "string"},
    "subscriberCount": {"type": "string"},
    "videoCount": {"type": "string"},
    "viewCount": {"type": "string"},
    "joinedDate": {"type": "string"},
    "country": {"type": "string"},
    "links": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "title": {"type": "string"},
                "url": {"type": "string"},
                "favicon": {
                    "type": "dict",
                    "schema": {
                        "sources": {
                            "type": "list",
                            "schema": {
                                "type": "dict",
                                "schema": {
                                    "url": {"type": "string"},
                                    "width": {"type": "integer"},
                                    "height": {"type": "integer"},
                                },
                            },
                        }
                    },
                },
            },
        },
    },
}

comments_schema = {
    "comment": {
        "type": "dict",
        "schema": {
            "id": {"type": "string"},
            "text": {"type": "string"},
            "publishedTime": {"type": "string"},
        },
    },
    "author": {
        "type": "dict",
        "schema": {
            "id": {"type": "string"},
            "displayName": {"type": "string"},
            "avatarThumbnail": {"type": "string"},
            "isVerified": {"type": "boolean"},
            "isCurrentUser": {"type": "boolean"},
            "isCreator": {"type": "boolean"},
        },
    },
    "stats": {
        "type": "dict",
        "schema": {
            "likeCount": {"type": "string"},
            "replyCount": {"type": "string"},
        },
    },
}

search_schema = {
    "id": {"type": "string"},
    "title": {"type": "string"},
    "description": {"type": "string", "nullable": True},
    "publishedTime": {"type": "string"},
    "videoLength": {"type": "string"},
    "viewCount": {"type": "string"},
    "videoBadges": {
        "type": "list",
        "nullable": True,
        "schema": {
            "type": "string",
            "nullable": True
        },
    },
    "channelBadges": {
        "type": "list",
        "nullable": True,
        "schema": {
            "type": "string",
            "nullable": True
        },
    },
    "videoThumbnails": _thumnails_schema,
    "channelThumbnails": _thumnails_schema,
    "url": {"type": "string"},
}

shorts_schema = {
    "videoId": {"type": "string"},
    "title": {"type": "string"},
    "lengthSeconds": {"type": "string"},
    "keywords": {
        "type": "list",
        "schema": {
            "type": "string"
        },
    },
    "channelId": {"type": "string"},
    "isOwnerViewing": {"type": "boolean"},
    "shortDescription": {"type": "string"},
    "isCrawlable": {"type": "boolean"},
    "thumbnail": _thumnails_schema,
    "allowRatings": {"type": "boolean"},
    "viewCount": {"type": "string"},
    "author": {"type": "string"},
    "isPrivate": {"type": "boolean"},
    "isUnpluggedCorpus": {"type": "boolean"},
    "isLiveContent": {"type": "boolean"},
}

video_schema = {
    "video": {
        "type": "dict",
        "schema": {
            "videoId": {"type": "string"},
            "title": {"type": "string"},
            "publishingDate": {"type": "string"},
            "lengthSeconds": {"type": "integer"},
            "keywords": {
                "type": "list",
                "nullable": True,
                "schema": {
                    "type": "string", "nullable": True
                },
            },
            "description": {"type": "string"},
            "thumbnail": _thumnails_schema,
            "stats": {
                "type": "dict",
                "schema": {
                    "viewCount": {"type": "integer"},
                    "likeCount": {"type": "integer"},
                    "commentCount": {"type": "integer", 'nullable': True},
                },
            },
        },
    },
    "channel": {
        "type": "dict",
        "schema": {
            "name": {"type": "string"},
            "identifierId": {"type": "string"},
            "id": {"type": "string"},
            "verified": {"type": "boolean"},
            "channelUrl": {"type": "string"},
            "subscriberCount": {"type": "string"},
            "thumbnails": {
                "type": "list",
                "schema": {
                    "type": "dict",
                    "schema": {"url": {"type": "string"}},
                },
            },
        },
    },
    "commentContinuationToken": {"type": "string"},
}


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_video_scraping():
    video_data = await youtube.scrape_video(
        ids=[
            "1Y-XvvWlyzk",
            "muo6I9XY8K4",
            "y7FbFJ4jOW8"
        ]
    )
    validator = Validator(video_schema, allow_unknown=True)
    for i in video_data:
        validate_or_fail(i, validator)
    assert len(video_data) == 3


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_comment_scraping():
    comment_data = await youtube.scrape_comments(
        video_id="FgakZw6K1QQ",
        max_scrape_pages=3
    )
    validator = Validator(comments_schema, allow_unknown=True)
    for i in comment_data:
        validate_or_fail(i, validator)
    assert len(comment_data) > 40


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_channel_scraping():
    channel_data = await youtube.scrape_channel(
        channel_ids=[
            "scrapfly"
        ]
    )
    validator = Validator(channel_schema, allow_unknown=True)
    for i in channel_data:
        validate_or_fail(i, validator)


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_channel_videos_scraping():
    channel_videos = await youtube.scrape_channel_videos(
        channel_id="statquest", sort_by="Latest", max_scrape_pages=3
    )
    validator = Validator(channel_videos_schema, allow_unknown=True)
    for i in channel_videos:
        validate_or_fail(i, validator)
    assert len(channel_videos) > 40


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_search_scraping():
    search_data = await youtube.scrape_search(
        search_query="python",
        search_params="EgQIAxAB",  # filter by video results only
        max_scrape_pages=3
    )
    validator = Validator(search_schema, allow_unknown=True)
    for i in search_data:
        validate_or_fail(i, validator)
    assert len(search_data) > 40


@pytest.mark.asyncio
@pytest.mark.flaky(reruns=3, reruns_delay=30)
async def test_shorts_scraping():
    shorts_data = await youtube.scrape_shorts(
        ids=[
            "rZ2qqtNPSBk"
        ]
    )
    validator = Validator(shorts_schema, allow_unknown=True)
    for i in shorts_data:
        validate_or_fail(i, validator)
