"""
This is an example web scraper for Facebook.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import re
import os
import json
import datetime
from typing import Dict, List, Optional
from urllib.parse import quote
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])


JS = [
    {"wait_for_selector": {"selector": "div[aria-label='Close']", "timeout": 3000}},
    {"click": {"selector": "div[aria-label='Close']"}},
    {"wait": 500},
    {"scroll": {"selector": "bottom"}},
]
BASE_CONFIG = {
    # bypass facebook.com web scraping blocking
    "asp": True,
    # set the proxy country to US
    "country": "US",
    "render_js": True,
    "js_scenario": JS,
    "proxy_pool": "public_residential_pool",
}


def parse_page(response: ScrapeApiResponse) -> Dict:
    """Parse Facebook page data from rendered HTML"""
    html = response.scrape_result["content"]
    sel = response.selector

    def og(prop: str) -> Optional[str]:
        return sel.xpath(f'//meta[@property="og:{prop}"]/@content').get()

    def card_text(card_type: str) -> Optional[str]:
        idx = html.find(f'"{card_type}"')
        if idx == -1:
            return None
        texts = re.findall(r'"text":"((?:[^"\\]|\\.)*)"', html[max(0, idx - 3000):idx])
        return json.loads(f'"{texts[-1]}"').replace(r"\/", "/") if texts else None
    
    def num(s: str) -> Optional[int]:
        return int(re.sub(r"\D", "", s)) if s else None

    desc = og("description") or ""
    m_likes = re.search(r"([\d,]+)\s*likes", desc)
    m_talking = re.search(r"([\d,]+)\s*talking about", desc)
    m_here = re.search(r"([\d,]+)\s*were here", desc)

    delegate = re.search(
        r'"delegate_page":\{"id":"(\d+)","category_name":"([^"]+)","name":"[^"]+","profile_picture_uri":"([^"]+)"'
        r'.*?"cover_photo":\{"photo":\{"image":\{"uri":"([^"]+)"',
        html,
    )
    intro_m = re.search(r'"best_description":\{"text":"([^"]+)"', html)
    page_url = og("url") or ""
    username_m = re.search(r"facebook\.com/([^/?\"]+)", page_url)

    price_raw = card_text("INTRO_CARD_BUSINESS_PRICE")
    price_m = re.search(r"Price Range\s*[\xb7·]\s*(\S+)", price_raw or "")

    rating_raw = card_text("INTRO_CARD_RATING")
    rating_m = re.search(r"(\d+)%\s*recommend\s*\(([0-9,]+)\s*Reviews?\)", rating_raw or "")

    map_url_m = re.search(r'"INTRO_CARD_ADDRESS"', html)
    map_url = None
    if map_url_m:
        chunk = html[max(0, map_url_m.start() - 3000):map_url_m.start()]
        mu = re.search(r'(https?:\\/\\/maps\.google\.com[^"]+)', chunk)
        map_url = mu.group(1).replace("\\/", "/").replace("\\u00252C", "%2C") if mu else None

    social = list(dict.fromkeys(
        u.replace("\\/", "/").encode().decode("unicode_escape")
        for u in re.findall(
            r'"url":"(https:\\/\\/(?:www\\.)?(?:instagram|twitter|x|youtube|linkedin|tiktok|pinterest)[^"]+)"',
            html,
        )
        if "l.php" not in u
    ))

    return {
        "name": (og("title") or "").split(" | ")[0].strip() or None,
        "username": username_m.group(1) if username_m else None,
        "url": page_url or None,
        "page_id": delegate.group(1) if delegate else None,
        "category": delegate.group(2).replace("\\/", "/") if delegate else None,
        "intro": intro_m.group(1) if intro_m else None,
        "likes": num(m_likes.group(1)) if m_likes else None,
        "talking_about": num(m_talking.group(1)) if m_talking else None,
        "were_here": num(m_here.group(1)) if m_here else None,
        "phone": card_text("INTRO_CARD_PROFILE_PHONE"),
        "email": card_text("INTRO_CARD_PROFILE_EMAIL"),
        "website": card_text("INTRO_CARD_WEBSITE"),
        "address": card_text("INTRO_CARD_ADDRESS"),
        "address_map_url": map_url,
        "price_range": price_m.group(1) if price_m else None,
        "recommend_percent": float(rating_m.group(1)) if rating_m else None,
        "review_count": num(rating_m.group(2)) if rating_m else None,
        "confirmed_owner": bool(card_text("INTRO_CARD_CONFIRMED_OWNER_LABEL")),
        "profile_picture_url": og("image"),
        "cover_photo_url": delegate.group(4).replace("\\/", "/") if delegate else None,
        "social_links": social or None,
    }


def parse_marketplace_listing(response: ScrapeApiResponse) -> List[Dict]:
    """parse marketplace listing data from HTML by extracting JSON from script tags"""

    def find_listings(obj, depth=0):
        """Recursively find all marketplace listing objects"""
        if depth > 50:
            return []
        if isinstance(obj, dict):
            results = [obj] if obj.get("__typename") in ["GroupCommerceProductItem", "MarketplaceProductItem"] else []
            return results + [item for value in obj.values() for item in find_listings(value, depth + 1)]
        return [
            item for sublist in (obj if isinstance(obj, list) else []) for item in find_listings(sublist, depth + 1)
        ]

    scripts = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', response.content, re.DOTALL)
    all_listings = []
    for script in scripts:
        try:
            all_listings.extend(find_listings(json.loads(script)))
        except (json.JSONDecodeError, Exception):
            continue

    parsed_listings = []
    for listing in all_listings:
        geocode = listing.get("location", {}).get("reverse_geocode", {})
        city, state = geocode.get("city", ""), geocode.get("state", "")
        location = f"{city}, {state}" if city and state else (city or state)

        parsed_listing = {
            "id": listing.get("id"),
            "title": listing.get("marketplace_listing_title"),
            "price": listing.get("formatted_price", {}).get("text", "N/A"),
            "location": location,
            "is_sold": listing.get("is_sold", False),
            "is_pending": listing.get("is_pending", False),
            "creation_time": listing.get("creation_time"),
        }

        if seller_data := listing.get("marketplace_listing_seller"):
            parsed_listing["seller"] = {"name": seller_data.get("name"), "id": seller_data.get("id")}
        if image := listing.get("primary_listing_photo", {}).get("image"):
            parsed_listing["image_url"] = image.get("uri")
        if delivery_types := listing.get("delivery_types"):
            parsed_listing["delivery_types"] = delivery_types
        if category_id := listing.get("marketplace_listing_category_id"):
            parsed_listing["category_id"] = category_id

        parsed_listings.append(parsed_listing)

    log.success(f"parsed {len(parsed_listings)} marketplace listings from the page")
    return parsed_listings


def parse_event(response: ScrapeApiResponse) -> List[Dict]:
    """parse event data from HTML by extracting JSON from script tags"""

    def find_events(obj):
        """Recursively find all Event objects"""
        if isinstance(obj, dict):
            results = [obj] if obj.get("__typename") == "Event" else []
            return results + [item for value in obj.values() for item in find_events(value)]
        return [item for sublist in (obj if isinstance(obj, list) else []) for item in find_events(sublist)]

    scripts = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', response.content, re.DOTALL)
    all_events = []
    for script in scripts:
        try:
            all_events.extend(find_events(json.loads(script)))
        except (json.JSONDecodeError, Exception):
            continue

    parsed_events = []
    for event in all_events:
        event_place = event.get("event_place", {})
        location = (
            event_place.get("contextual_name", "")
            if event_place
            else ("Online Event" if event.get("is_online") else "")
        )

        parsed_event = {
            "id": event.get("id"),
            "title": event.get("name"),
            "date": event.get("day_time_sentence"),
            "location": location,
            "url": event.get("url") or event.get("eventUrl"),
            "start_timestamp": event.get("start_timestamp"),
            "is_online": event.get("is_online", False),
            "event_kind": event.get("event_kind"),
            "is_past": event.get("is_past", False),
            "is_happening_now": event.get("is_happening_now", False),
            "is_hosted_by_ticket_master": event.get("is_hosted_by_ticket_master", False),
        }

        if event_place:
            parsed_event["location_details"] = {"name": event_place.get("contextual_name"), "id": event_place.get("id")}
        if photo := (event.get("cover_photo") or {}).get("photo"):
            parsed_event["cover_photo"] = {
                "url": (photo.get("eventImage") or {}).get("uri"),
                "accessibility_caption": photo.get("accessibility_caption"),
                "id": photo.get("id"),
            }
        if social_context := event.get("social_context"):
            parsed_event["social_context"] = social_context.get("text")
        if price_range := (event.get("ticketing_context_row") or {}).get("price_range_text"):
            parsed_event["price_range"] = price_range

        parsed_events.append(parsed_event)

    log.success(f"parsed {len(parsed_events)} events from the page")
    return parsed_events


async def scrape_facebook_events(event_name: str = "New York, NY") -> List[Dict]:
    log.info(f"scraping Facebook Events for event: {event_name}")

    # build events URL with location
    url = f"https://www.facebook.com/events/search?q={quote(event_name)}&sde=Abq6hpNmijm8kReC4KYmmDP0NuT4IxNliFRnd3vuRZUj8uh4BsVIK3dVq186DripYNQbuwiy5LR0V3y0W_iqLV_W"
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=url,
            **BASE_CONFIG,
        )
    )

    # Parse events from the response
    events = parse_event(result)

    log.success(f"scraped {len(events)} events from {event_name}")
    return events


async def scrape_marketplace_listings(query: str = "electronics") -> List[Dict]:
    """Scrape Facebook Marketplace listings for a specific query"""
    log.info(f"scraping Facebook Marketplace listings for query: {query}")

    # build marketplace URL with location
    url = f"https://www.facebook.com/marketplace/search/?query={quote(query)}"
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=url,
            **BASE_CONFIG,
        )
    )
    listings = parse_marketplace_listing(result)

    log.success(f"scraped {len(listings)} marketplace listings from {query}")
    return listings


async def scrape_facebook_page(page_urls: list[str]) -> list[Dict]:
    """Scrape a Facebook page and return a FacebookPage"""
    results = []
    for url in page_urls:
        result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
        results.append(parse_page(result))
    return results


def parse_group_posts(response: ScrapeApiResponse) -> List[Dict]:
    """Parse Facebook group posts from rendered HTML"""
    html = response.scrape_result["content"]
    sel = response.selector

    group_name = (sel.xpath('//meta[@property="og:title"]/@content').get() or "").split(" | ")[0].strip() or None
    group_url = sel.xpath('//meta[@property="og:url"]/@content').get()

    def find(obj, typename, depth=0):
        if depth > 60 or not isinstance(obj, (dict, list)):
            return []
        if isinstance(obj, list):
            return [r for el in obj for r in find(el, typename, depth + 1)]
        res = [obj] if obj.get("__typename") == typename else []
        return res + [r for v in obj.values() for r in find(v, typename, depth + 1)]

    def find_comments(obj, depth=0):
        """Find comment nodes that have both preferred_body and an author renderer."""
        if depth > 60 or not isinstance(obj, (dict, list)):
            return []
        if isinstance(obj, list):
            return [r for el in obj for r in find_comments(el, depth + 1)]
        res = [obj] if (obj.get("preferred_body") and obj.get("comet_comment_author_name_and_badges_renderer")) else []
        return res + [r for v in obj.values() for r in find_comments(v, depth + 1)]

    stories, feedback, comments = {}, {}, {}

    for script in re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL):
        try:
            data = json.loads(script)
        except (json.JSONDecodeError, Exception):
            continue

        for s in find(data, "Story"):
            if (pid := s.get("post_id")) and pid not in stories:
                stories[pid] = s

        for r in find(data, "UnauthenticatedUCometUFISummaryAndActionsRenderer"):
            fb = r.get("feedback") or {}
            if tid := fb.get("subscription_target_id"):
                feedback[tid] = fb

        for node in find_comments(data):
            c = (node.get("comet_comment_author_name_and_badges_renderer") or {}).get("comment") or {}
            parent = (c.get("parent_feedback") or {}).get("share_fbid")
            if not parent:
                continue
            comments.setdefault(parent, []).append({
                "author": (c.get("user") or {}).get("name"),
                "text": (node.get("preferred_body") or {}).get("text"),
            })

    results = []
    for post_id, story in stories.items():
        actors = story.get("actors") or []
        ct = story.get("creation_time")

        msg, msg_ranges = None, []
        try:
            m = story["comet_sections"]["content"]["story"]["comet_sections"]["message"]["story"]["message"]
            msg, msg_ranges = m.get("text"), m.get("ranges") or []
        except (KeyError, TypeError):
            pass

        fb = feedback.get(str(post_id)) or {}
        
        cr = fb.get("comment_rendering_instance") or {}

        media_urls, link_title, link_url = [], None, None
        for att in story.get("attachments") or []:
            ad = (att.get("styles") or {}).get("attachment") or {}
            for node in (ad.get("all_subattachments") or {}).get("nodes") or []:
                if uri := ((node.get("media") or {}).get("image") or {}).get("uri"):
                    media_urls.append(uri)
            img = (ad.get("media") or {}).get("photo_image") or (ad.get("media") or {}).get("image") or {}
            if uri := img.get("uri"):
                media_urls.append(uri)
            if isinstance(ad.get("title"), dict) and ad["title"].get("text"):
                link_title, link_url = ad["title"]["text"], ad.get("url")

        results.append({
            "post_url": story.get("permalink_url"),
            "group": group_name,
            "group_url": group_url,
            "posted_at": datetime.datetime.fromtimestamp(ct, datetime.timezone.utc).isoformat().replace("+00:00", "Z") if ct else None,
            "text": msg,
            "author": actors[0].get("name") if actors else None,
            "reactions": (fb.get("reaction_count") or {}).get("count"),
            "comments": (cr.get("comments") or {}).get("total_count") or fb.get("total_comment_count"),
            "shares": (fb.get("share_count") or {}).get("count"),
            "link_title": link_title,
            "link_url": link_url,
            "media": media_urls or None,
            "mentions": [r["entity"]["name"] for r in msg_ranges if r.get("entity", {}).get("__typename") == "User" and r["entity"].get("name")] or None,
            "top_comments": comments.get(str(post_id)) or None,
        })

    log.success(f"parsed {len(results)} group posts from {group_url}")
    return results


async def scrape_group_posts(group_urls: List[str]) -> List[Dict]:
    """Scrape posts from one or more public Facebook groups"""
    all_posts = []
    for url in group_urls:
        log.info(f"scraping Facebook group posts from {url}")
        result = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
        posts = parse_group_posts(result)
        all_posts.extend(posts)
        log.success(f"scraped {len(posts)} posts from {url}")
    return all_posts
