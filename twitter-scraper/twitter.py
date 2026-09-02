"""
This is an example web scraper for Twitter.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-twitter/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os

from typing import Dict, List, Optional

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # X.com (Twitter) requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
}


def _find_ld_json(scripts: List[str], type_: str) -> Optional[Dict]:
    """find a JSON-LD script block by schema type"""
    for script in scripts:
        try:
            data = json.loads(script)
        except json.JSONDecodeError:
            continue
        if data.get("@type") == type_:
            return data
    return None


def _interaction_count(stats: List[Dict], name: str = None, interaction_type: str = None) -> Optional[int]:
    """get interaction count by stat name or interaction type"""
    for stat in stats or []:
        if name and stat.get("name") == name:
            return stat.get("userInteractionCount")
        if interaction_type and stat.get("interactionType", "").endswith(interaction_type):
            return stat.get("userInteractionCount")
    return None


async def scrape_tweet(url: str) -> Dict:
    """scrape a tweet page and return text, author and engagement stats"""
    log.info("scraping tweet {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    scripts = result.selector.xpath('//script[@type="application/ld+json"]/text()').getall()
    data = _find_ld_json(scripts, "SocialMediaPosting")
    if not data:
        raise Exception(f"Failed to find tweet data on {url}")
    stats = data.get("interactionStatistic", [])
    author = data.get("author", {})
    return {
        "id": data.get("identifier"),
        "url": data.get("url") or data.get("mainEntityOfPage"),
        "text": data.get("articleBody") or data.get("text"),
        "created_at": data.get("dateCreated") or data.get("datePublished"),
        "reply_count": data.get("commentCount") or _interaction_count(stats, name="Replies"),
        "retweet_count": _interaction_count(stats, name="Retweets"),
        "favorite_count": _interaction_count(stats, name="Likes"),
        "view_count": _interaction_count(stats, interaction_type="ViewAction"),
        "user": {
            "name": author.get("name"),
            "screen_name": (author.get("alternateName") or "").lstrip("@"),
            "url": author.get("url"),
        },
    }


async def scrape_profile(url: str) -> Dict:
    """scrape a user profile page and return profile data"""
    log.info("scraping profile {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    scripts = result.selector.xpath('//script[@type="application/ld+json"]/text()').getall()
    data = _find_ld_json(scripts, "ProfilePage")
    if not data:
        raise Exception(f"Failed to find profile data on {url}")
    user = data.get("mainEntity", {})
    stats = user.get("interactionStatistic", [])
    image = user.get("image", {})
    return {
        "id": user.get("identifier"),
        "rest_id": user.get("identifier"),
        "name": user.get("name"),
        "screen_name": user.get("additionalName"),
        "description": user.get("description"),
        "location": (user.get("homeLocation") or {}).get("name"),
        "website": user.get("sameAs"),
        "profile_image_url": image.get("contentUrl"),
        "created_at": data.get("dateCreated"),
        "followers_count": _interaction_count(stats, interaction_type="FollowAction"),
        "friends_count": _interaction_count(stats, interaction_type="SubscribeAction"),
        "statuses_count": _interaction_count(stats, interaction_type="WriteAction"),
    }
