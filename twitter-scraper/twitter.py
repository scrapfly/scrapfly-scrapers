"""
This is an example web scraper for Twitter.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-twitter/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import re
import os
import base64
import datetime
from html import unescape
from typing import Dict, List, Optional

from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # X.com (Twitter) requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "render_js": True,
    "auto_scroll": True,
    "rendering_wait": 2000,
    "country": "US",
}


def meta(sel, *, name: str = None, prop: str = None) -> Optional[str]:
    """read a meta tag by name or property"""
    if name:
        return sel.xpath(f'//meta[@name="{name}"]/@content').get()
    return sel.xpath(f'//meta[@property="{prop}"]/@content').get()


def parse_count(text: Optional[str]) -> Optional[int]:
    """parse compact counts like 2.2K, 2 k, or 5&nbsp;M"""
    if not text:
        return None
    text = text.replace("&nbsp;", "").replace("\u00a0", "").replace(" ", "").replace(",", "")
    match = re.match(r"^(\d+(?:\.\d+)?)([KMB])?$", text, re.I)
    if not match:
        return None
    mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get((match.group(2) or "").upper(), 1)
    return int(float(match.group(1)) * mult)


def icon_count(html: str, icon: str) -> Optional[int]:
    """read a count next to a stable icon (locale-independent)"""
    start = html.find(f'data-icon="icon-{icon}"')
    if start == -1:
        return None
    end = html.find('data-icon="icon-', start + 1)
    chunk = html[start: end if end != -1 else start + 2000]
    nums = [t.strip() for t in re.findall(r">([^<>]+)<", chunk) if re.match(r"^\d", t.strip())]
    return parse_count(nums[-1]) if nums else None


def icon_text(html: str, icon: str) -> Optional[str]:
    """read text shown after a stable icon (location, etc.)"""
    match = re.search(rf'data-icon="icon-{icon}".*?font-normal">([^<]+)<', html)
    return unescape(match.group(1)) if match else None


def website_url(html: str) -> Optional[str]:
    """read profile website link next to the link icon"""
    match = re.search(r'data-icon="icon-link".*?href="(https://t\.co/\w+)"', html)
    return match.group(1) if match else None


def href_count(html: str, path: str) -> Optional[int]:
    """read a profile stat via a stable href path"""
    match = re.search(rf'href="[^"]*{re.escape(path)}"[^>]*><div[^>]*><div[^>]*>([^<]+)</div>', html)
    return parse_count(match.group(1)) if match else None


def views_count(html: str, tweet_id: str) -> Optional[int]:
    """read view count from the tweet permalink (locale-independent)"""
    match = re.search(rf'href="/\w+/status/{re.escape(tweet_id)}"[^>]*><span[^>]*>([^<]+)</span>', html)
    return parse_count(match.group(1)) if match else None


def author_name(title: Optional[str]) -> Optional[str]:
    match = re.match(r"^(.+?)\s*\(@", title or "")
    return match.group(1) if match else None


def twitter_date(ms: Optional[str]) -> Optional[str]:
    if not ms:
        return None
    dt = datetime.datetime.fromtimestamp(int(ms) / 1000, tz=datetime.timezone.utc)
    return dt.strftime("%a %b %d %H:%M:%S +0000 %Y")


def user_gid(rest_id: Optional[str]) -> Optional[str]:
    return base64.b64encode(f"User:{rest_id}".encode()).decode() if rest_id else None


def unique(pattern: str, text: str) -> List[str]:
    return list(dict.fromkeys(re.findall(pattern, text)))


def parse_tweet(response: ScrapeApiResponse) -> Dict:
    """parse a rendered tweet/status page"""
    html = response.scrape_result["content"]
    sel = response.selector

    url = meta(sel, prop="og:url")
    tweet_id = re.search(r"/status/(\d+)", url or "")
    tweet_id = tweet_id.group(1) if tweet_id else None
    text = unescape(meta(sel, prop="og:description") or "") or None
    ts = re.search(r'"timestamp":(\d+)', html)
    media = unique(r'src="(https://pbs\.twimg\.com/media/[^"]+)"', html)
    views = views_count(html, tweet_id) if tweet_id else None

    return {
        "id": tweet_id,
        "conversation_id": tweet_id,
        "url": url,
        "text": text,
        "created_at": twitter_date(ts.group(1)) if ts else None,
        "language": sel.xpath("//html/@lang").get(),
        "attached_urls": unique(r"https://t\.co/\w+", text or ""),
        "attached_media": [unescape(u) for u in media] or None,
        "tagged_users": unique(r"@(\w+)", text or ""),
        "tagged_hashtags": unique(r"#(\w+)", text or ""),
        "reply_count": icon_count(html, "reply-stroke"),
        "retweet_count": icon_count(html, "retweet-stroke"),
        "favorite_count": icon_count(html, "heart-stroke"),
        "bookmark_count": icon_count(html, "bookmark-stroke"),
        "views": str(views) if views is not None else None,
        "user": {
            "name": author_name(meta(sel, prop="og:title")),
            "screen_name": (meta(sel, name="twitter:creator") or "").lstrip("@") or None,
            "profile_image_url": meta(sel, prop="og:image"),
            "verified": 'data-icon="icon-verified"' in html,
        },
    }


def parse_profile(response: ScrapeApiResponse) -> Dict:
    """parse a rendered profile page"""
    html = response.scrape_result["content"]
    sel = response.selector

    rest_id = re.search(r"profile_banners/(\d+)/", html)
    rest_id = rest_id.group(1) if rest_id else None
    description = unescape(meta(sel, prop="og:description") or "") or None
    website = website_url(html)
    bio_urls = unique(r"https://t\.co/\w+", description or "")
    followers = href_count(html, "/verified_followers")

    return {
        "id": user_gid(rest_id),
        "rest_id": rest_id,
        "name": author_name(meta(sel, prop="og:title")),
        "screen_name": (meta(sel, name="twitter:creator") or "").lstrip("@") or None,
        "verified": 'data-icon="icon-verified"' in html,
        "description": description,
        "location": icon_text(html, "location-stroke"),
        "joined": meta(sel, name="twitter:data2") if meta(sel, name="twitter:label2") == "Joined" else None,
        "url": website,
        "profile_image_url": meta(sel, prop="og:image"),
        "profile_banner_url": meta(sel, name="twitter:image"),
        "followers_count": followers,
        "friends_count": href_count(html, "/following"),
        "statuses_count": parse_count(meta(sel, name="twitter:data1")),
        "fast_followers_count": 0,
        "entities": {
            "description": {"urls": [{"url": u} for u in bio_urls]},
            "url": {"urls": [{"url": website}] if website else []},
        },
    }


async def scrape_tweet(url: str) -> Dict:
    """scrape a tweet page"""
    log.info("scraping tweet {}", url)
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    return parse_tweet(response)


async def scrape_profile(url: str) -> Dict:
    """scrape a profile page"""
    log.info("scraping profile {}", url)
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    return parse_profile(response)
