"""
This is an example web scraper for Twitter.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-twitter/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import os
import re
from typing import Dict, List, Optional

from loguru import logger as log
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # X.com (Twitter) requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
}


def _meta(scope, prop: str, own: bool = False) -> Optional[str]:
    if own:
        return scope.xpath(f'./meta[@itemprop="{prop}"]/@content').get()
    return scope.css(f'meta[itemprop="{prop}"]::attr(content)').get()


def _int(val: Optional[str]) -> Optional[int]:
    return int(val) if val else None


def _stat(scope, action: str) -> Optional[int]:
    for stat in scope.css("[itemprop=interactionStatistic]"):
        if action in (_meta(stat, "interactionType") or ""):
            return _int(_meta(stat, "userInteractionCount"))
    return None


def _parse_post(post) -> Dict:
    author = post.css("[itemprop=author]")
    tweet_id = _meta(post, "identifier")
    in_reply_to_url = _meta(post, "isPartOf", own=True)
    quoted_tweet_url = _meta(post, "isBasedOn", own=True)
    images = post.xpath(
        './/*[@itemprop="image" and @itemtype="https://schema.org/ImageObject" '
        'and not(ancestor::*[@itemprop="hasPart"])]'
    )
    return {
        "id": tweet_id,
        "conversation_id": tweet_id,
        "url": _meta(post, "url"),
        "text": _meta(post, "articleBody") or _meta(post, "text"),
        "created_at": _meta(post, "dateCreated") or _meta(post, "datePublished"),
        "reply_count": int(_meta(post, "commentCount") or 0) or _stat(post, "ReplyAction") or 0,
        "retweet_count": _stat(post, "ShareAction") or 0,
        "quote_count": _stat(post, "InteractAction"),
        "favorite_count": _stat(post, "LikeAction"),
        "view_count": _stat(post, "ViewAction"),
        "user": {
            "name": _meta(author, "name"),
            "screen_name": (_meta(author, "alternateName") or "").lstrip("@"),
            "url": _meta(author, "url"),
            "profile_image_url": _meta(author, "image"),
        },
        "is_reply": bool(in_reply_to_url),
        "in_reply_to_url": in_reply_to_url,
        "is_quote": bool(quoted_tweet_url),
        "quoted_tweet_url": quoted_tweet_url,
        "media": [
            {
                "url": _meta(image, "contentUrl", own=True),
                "thumbnail_url": _meta(image, "thumbnailUrl", own=True),
                "width": _int(_meta(image, "width", own=True)),
                "height": _int(_meta(image, "height", own=True)),
            }
            for image in images
        ],
    }


def parse_tweet(response: ScrapeApiResponse, url: str) -> Dict:
    """parse tweet data from schema.org markup on a tweet page"""
    tweet_id = re.search(r"/status/(\d+)", url)
    tweet_id = tweet_id.group(1) if tweet_id else None
    posts = response.selector.css('[itemtype="https://schema.org/SocialMediaPosting"]')
    post = next((p for p in posts if _meta(p, "identifier") == tweet_id), None) if tweet_id else None
    post = post or (posts[0] if posts else None)
    if not post:
        raise Exception(f"Failed to find tweet data on {url}")
    return _parse_post(post)


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
        "screen_name": _meta(entity, "additionalName") or "",
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


async def scrape_tweet(url: str) -> Dict:
    """scrape a tweet page and return text, author and engagement stats"""
    log.info("scraping tweet {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    return parse_tweet(result, url)


async def scrape_profile(url: str) -> Dict:
    """scrape a user profile page and return profile data"""
    log.info("scraping profile {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, auto_scroll=True, **BASE_CONFIG))
    return parse_profile(result)
