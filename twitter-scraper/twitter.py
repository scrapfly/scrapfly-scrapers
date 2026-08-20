"""
This is an example web scraper for Twitter.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-twitter/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
from typing import Dict, Optional

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # X.com (Twitter) requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
}
SYNDICATION_API = "https://cdn.syndication.twimg.com/tweet-result"


def _meta(scope, prop: str, own: bool = False) -> Optional[str]:
    if own:
        return scope.xpath(f'./meta[@itemprop="{prop}"]/@content').get()
    return scope.css(f'meta[itemprop="{prop}"]::attr(content)').get()


def _int(val) -> Optional[int]:
    try:
        return int(val) if val not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _stat(scope, action: str) -> Optional[int]:
    for stat in scope.css("[itemprop=interactionStatistic]"):
        if action in (_meta(stat, "interactionType") or ""):
            return _int(_meta(stat, "userInteractionCount"))
    return None


def parse_tweet(data: Dict) -> Dict:
    """parse tweet dataset of X.com's embed (syndication) API"""
    user = data.get("user") or {}
    quoted = data.get("quoted_tweet") or {}
    quoted_user = quoted.get("user") or {}
    entities = data.get("entities") or {}
    reply_id = data.get("in_reply_to_status_id_str")
    tweet_id = data.get("id_str")
    screen_name = user.get("screen_name") or ""
    return {
        "id": tweet_id,
        "conversation_id": (data.get("parent") or {}).get("id_str") or reply_id or tweet_id,
        "url": f"https://x.com/{screen_name}/status/{tweet_id}",
        "text": data.get("text"),
        "lang": data.get("lang"),
        "created_at": data.get("created_at"),
        "reply_count": data.get("conversation_count") or 0,
        # retweet and view counts are not exposed to logged out visitors
        "retweet_count": 0,
        "favorite_count": data.get("favorite_count"),
        "is_edited": bool(data.get("isEdited")),
        "user": {
            "id": user.get("id_str"),
            "name": user.get("name"),
            "screen_name": screen_name,
            "url": f"https://x.com/{screen_name}" if screen_name else None,
            "profile_image_url": (user.get("profile_image_url_https") or "").replace("_normal.", "_400x400.") or None,
            "verified": bool(user.get("is_blue_verified")),
            "business_label": (user.get("highlighted_label") or {}).get("description"),
        },
        "is_reply": bool(reply_id),
        "in_reply_to_url": (
            f"https://x.com/{data.get('in_reply_to_screen_name')}/status/{reply_id}" if reply_id else None
        ),
        "is_quote": bool(quoted),
        "quoted_tweet_url": (
            f"https://x.com/{quoted_user.get('screen_name')}/status/{quoted.get('id_str')}" if quoted else None
        ),
        "attached_urls": [u.get("expanded_url") for u in entities.get("urls") or []],
        "tagged_users": [m.get("screen_name") for m in entities.get("user_mentions") or []],
        "tagged_hashtags": [h.get("text") for h in entities.get("hashtags") or []],
        "media": [
            {
                "url": m.get("media_url_https"),
                "type": m.get("type"),
                "width": (m.get("original_info") or {}).get("width"),
                "height": (m.get("original_info") or {}).get("height"),
            }
            for m in data.get("mediaDetails") or []
        ],
    }


def _parse_post(post) -> Dict:
    """parse tweet from schema.org microdata (tweets listed on profile pages)"""
    author = post.css("[itemprop=author]")
    tweet_id = _meta(post, "identifier") or post.attrib.get("data-tweet-id")
    screen_name = (_meta(author, "alternateName") or _meta(author, "additionalName") or "").lstrip("@")
    quote_href = post.xpath('.//*[@data-href][not(ancestor::*[@data-href])][1]/@data-href').get()
    images = post.xpath(
        './/*[@itemprop="image" and @itemtype="https://schema.org/ImageObject" '
        'and not(ancestor::*[@itemprop="hasPart"])]'
    )
    return {
        "id": tweet_id,
        "conversation_id": tweet_id,
        "url": _meta(post, "url") or (f"https://x.com/{screen_name}/status/{tweet_id}" if tweet_id and screen_name else None),
        "text": _meta(post, "articleBody") or _meta(post, "text"),
        "created_at": _meta(post, "dateCreated") or _meta(post, "datePublished"),
        "reply_count": _int(_meta(post, "commentCount")) or _stat(post, "ReplyAction") or 0,
        "retweet_count": 0,
        "favorite_count": _stat(post, "LikeAction"),
        "user": {
            "name": _meta(author, "name"),
            "screen_name": screen_name,
            "url": _meta(author, "url") or (f"https://x.com/{screen_name}" if screen_name else None),
            "profile_image_url": _meta(author, "image"),
        },
        "is_reply": bool(_meta(post, "isPartOf", own=True)),
        "in_reply_to_url": _meta(post, "isPartOf", own=True),
        "is_quote": bool(quote_href),
        "quoted_tweet_url": f"https://x.com{quote_href}" if quote_href else None,
        "media": [
            {
                "url": _meta(img, "contentUrl", own=True),
                "thumbnail_url": _meta(img, "thumbnailUrl", own=True),
                "width": _int(_meta(img, "width", own=True)),
                "height": _int(_meta(img, "height", own=True)),
            }
            for img in images
        ],
    }


def parse_profile(response: ScrapeApiResponse) -> Dict:
    """parse profile data from schema.org markup on a profile page"""
    sel = response.selector
    page = sel.css('[itemtype="https://schema.org/ProfilePage"]')
    if not page:
        raise Exception("Failed to find profile data")

    entity = page.css("[itemprop=mainEntity]")
    image = entity.css("[itemprop=image]")
    user_id = _meta(entity, "identifier")

    statuses_count = friends_count = followers_count = 0
    for stat in entity.css('[itemprop=agentInteractionStatistic], [itemprop=interactionStatistic]'):
        action = _meta(stat, "interactionType") or ""
        count = int(_meta(stat, "userInteractionCount") or 0)
        if "WriteAction" in action:
            statuses_count = count
        elif "FollowAction" in action:
            if (_meta(stat, "name") or "").lower() == "following":
                friends_count = count
            else:
                followers_count = count

    banner = sel.css('meta[name="twitter:image"]::attr(content)').get()
    if not banner or "profile_banners" not in banner:
        srcset = sel.css('link[rel=preload][imagesrcset*="profile_banners"]::attr(imagesrcset)').get()
        if srcset:
            banner = srcset.rsplit(",", 1)[-1].strip().split(" ")[0]

    return {
        "id": user_id,
        "rest_id": user_id,
        "url": _meta(entity, "url") or sel.css('meta[property="og:url"]::attr(content)').get(),
        "name": _meta(entity, "name"),
        "screen_name": (_meta(entity, "alternateName") or _meta(entity, "additionalName") or "").lstrip("@"),
        "description": _meta(entity, "description"),
        "location": _meta(entity.css("[itemprop=homeLocation]"), "name"),
        "website": _meta(entity, "sameAs"),
        "related_links": entity.css("meta[itemprop=relatedLink]::attr(content)").getall(),
        "profile_image_url": _meta(image, "contentUrl"),
        "profile_image_thumbnail_url": _meta(image, "thumbnailUrl"),
        "profile_banner_url": banner,
        "created_at": _meta(page, "dateCreated"),
        "joined": sel.css('meta[name="twitter:data2"]::attr(content)').get(),
        "verified": bool(page.css('[data-icon*="verified"]')),
        "statuses_count": statuses_count,
        "friends_count": friends_count,
        "followers_count": followers_count,
        "tweets": [_parse_post(post) for post in sel.css('[itemtype="https://schema.org/SocialMediaPosting"]')],
    }


async def scrape_tweet(tweet_id: str) -> Dict:
    """scrape a tweet using X.com's public embed widget API"""
    log.info("scraping tweet {}", tweet_id)
    url = f"{SYNDICATION_API}?id={tweet_id}&token=x&lang=en"
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = json.loads(result.content)
    if not data.get("id_str"):
        raise Exception(f"Failed to find tweet data for id {tweet_id}")
    return parse_tweet(data)


async def scrape_profile(url: str) -> Dict:
    """scrape a user profile page and return profile data"""
    log.info("scraping profile {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, auto_scroll=True, **BASE_CONFIG))
    return parse_profile(result)
