"""
This is an example web scraper for Instagram.com used in scrapfly blog article:
https://scrapfly.io/blog/how-to-scrape-instagram/

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""
import json
import os
from typing import Dict, Optional
from urllib.parse import quote, urlencode
import jmespath
import re
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient


SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])
BASE_CONFIG = {
    # Instagram.com requires Anti Scraping Protection bypass feature.
    # for more: https://scrapfly.io/docs/scrape-api/anti-scraping-protection
    "asp": True,
    "country": "CA",  # change country for relevant results
}
INSTAGRAM_APP_ID = "936619743392459"  # this is the public app id for instagram.com
INSTAGRAM_DOCUMENT_ID = "8845758582119845" # constant id for post documents instagram.com
INSTAGRAM_ACCOUNT_DOCUMENT_ID = "9310670392322965"

# scroll down the comments section to load them
COMMENTS_JS_SCENARIO = [
    {"wait": 2000},
    {
        "wait_for_selector": {
            "selector": '//*[local-name()="svg" and @*[local-name()="aria-label"]="Comment"]'
        }
    },
    {
        "click": {
            "selector": '//*[local-name()="svg" and @*[local-name()="aria-label"]="Close"]',
            "ignore_if_not_visible": True,
        }
    },
    {
        "execute": {
            "script": "function scrollComments(pct, intervalMs, times) {\n  pct = pct || 0.3;\n  intervalMs = intervalMs || 500;\n  times = times || 20;\n  return new Promise(function(resolve) {\n    var el = document.querySelector('div.x5yr21d.xw2csxc.x1odjw0f.x1n2onr6');\n    if (!el) { resolve(); return; }\n    var count = 0;\n    var timer = setInterval(function() {\n      var delta = el.scrollHeight * pct;\n      el.scrollTop += delta;\n      count++;\n      if (count >= times) {\n        clearInterval(timer);\n        resolve();\n      }\n    }, intervalMs);\n  });\n}\nreturn scrollComments(0.3, 500, 20);\n",
            "timeout": 20000,
        }
    },
]

def parse_user(data: Dict) -> Dict:
    """Reduce the user data to the relevant fields"""
    log.debug("parsing user data {}", data["username"])
    result = jmespath.search(
        """{
        name: full_name,
        username: username,
        id: id,
        category: category_name,
        business_category: business_category_name,
        phone: business_phone_number,
        email: business_email,
        bio: biography,
        bio_links: bio_links[].url,
        homepage: external_url,        
        followers: edge_followed_by.count,
        follows: edge_follow.count,
        facebook_id: fbid,
        is_private: is_private,
        is_verified: is_verified,
        profile_image: profile_pic_url_hd,
        video_count: edge_felix_video_timeline.count,
        videos: edge_felix_video_timeline.edges[].node.{
            id: id, 
            title: title,
            shortcode: shortcode,
            thumb: display_url,
            url: video_url,
            views: video_view_count,
            tagged: edge_media_to_tagged_user.edges[].node.user.username,
            captions: edge_media_to_caption.edges[].node.text,
            comments_count: edge_media_to_comment.count,
            comments_disabled: comments_disabled,
            taken_at: taken_at_timestamp,
            likes: edge_liked_by.count,
            location: location.name,
            duration: video_duration
        },
        image_count: edge_owner_to_timeline_media.count,
        images: edge_felix_video_timeline.edges[].node.{
            id: id, 
            title: title,
            shortcode: shortcode,
            src: display_url,
            url: video_url,
            views: video_view_count,
            tagged: edge_media_to_tagged_user.edges[].node.user.username,
            captions: edge_media_to_caption.edges[].node.text,
            comments_count: edge_media_to_comment.count,
            comments_disabled: comments_disabled,
            taken_at: taken_at_timestamp,
            likes: edge_liked_by.count,
            location: location.name,
            accesibility_caption: accessibility_caption,
            duration: video_duration
        },
        saved_count: edge_saved_media.count,
        collections_count: edge_saved_media.count,
        related_profiles: edge_related_profiles.edges[].node.username
    }""",
        data,
    )
    return result


async def scrape_user(username: str) -> Dict:
    """Scrape instagram user's data"""
    log.info("scraping instagram user {}", username)
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}",
            headers={
                "x-ig-app-id": INSTAGRAM_APP_ID,
                },
            **BASE_CONFIG,
        )
    )
    data = json.loads(result.content)
    return parse_user(data["data"]["user"])


def parse_comments(data: Dict) -> Dict:
    """Parse the comments data from the post dataset"""
    if "edge_media_to_comment" in data:
        return jmespath.search(
            """{
                comments_count: edge_media_to_comment.count,
                comments_disabled: comments_disabled,
                comments_next_page: edge_media_to_comment.page_info.end_cursor,
                comments: edge_media_to_comment.edges[].node.{
                    id: id,
                    text: text,
                    created_at: created_at,
                    owner_id: owner.id,
                    owner: owner.username,
                    owner_verified: owner.is_verified,
                    viewer_has_liked: viewer_has_liked
                }
            }""",
            data,
        )
    else:
        return jmespath.search(
            """{
                comments_count: edge_media_to_parent_comment.count,
                comments_disabled: comments_disabled,
                comments_next_page: edge_media_to_parent_comment.page_info.end_cursor,
                comments: edge_media_to_parent_comment.edges[].node.{
                    id: id,
                    text: text,
                    created_at: created_at,
                    owner: owner.username,
                    owner_verified: owner.is_verified,
                    viewer_has_liked: viewer_has_liked,
                    likes: edge_liked_by.count
                }
            }""",
            data,
        )


def _extract_xig_polaris_media(html: str) -> Optional[Dict]:
    scripts = re.findall(
        r'<script[^>]*data-sjs[^>]*>(.*?)</script>', html, re.DOTALL
    )
    for script in scripts:
        if "xig_polaris_media" not in script:
            continue
        try:
            payload = json.loads(script)
            modules = payload["require"][0][3][0]["__bbox"]["require"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            continue
        for module in modules:
            if not isinstance(module, list) or len(module) <= 3:
                continue
            for entry in module[3]:
                if not isinstance(entry, dict):
                    continue
                media = (
                    entry.get("__bbox", {})
                    .get("result", {})
                    .get("data", {})
                    .get("xig_polaris_media")
                )
                if media:
                    return media
    return None


def parse_post(data: Dict) -> Dict:
    """Parse post data from the xig_polaris_media HTML-embedded structure"""
    post = data.get("if_not_gated_logged_out") or data
    caption_text = (post.get("caption") or {}).get("text")

    comments = []
    for edge in (data.get("comments_connection") or {}).get("edges") or []:
        node = edge.get("node")
        if not node:
            continue
        user = node.get("user") or {}
        comments.append({
            "id": str(node.get("pk", "")),
            "text": node.get("text", ""),
            "created_at": node.get("created_at"),
            "owner": user.get("username", ""),
            "owner_id": str(user.get("pk", "")),
            "owner_verified": user.get("is_verified", False),
            "likes": node.get("comment_like_count", 0),
        })

    return {
        "id": str(post.get("pk", "")),
        "shortcode": post.get("code", ""),
        "src": post.get("display_uri", ""),
        "src_attached": [
            m["display_uri"]
            for m in post.get("carousel_media") or []
            if m.get("display_uri")
        ],
        "likes": post.get("like_count"),
        "taken_at": post.get("taken_at"),
        "location": (post.get("location") or {}).get("name"),
        "captions": [caption_text] if caption_text else [],
        "comments_count": post.get("comment_count"),
        "comments": comments,
    }


async def scrape_post(url_or_shortcode: str) -> Dict:
    """Scrape single Instagram post data by parsing the HTML page"""
    if "http" not in url_or_shortcode:
        url = f"https://www.instagram.com/p/{url_or_shortcode}/"
    else:
        url = url_or_shortcode
    
    log.info("scraping instagram post: {}", url)
    result = await SCRAPFLY.async_scrape(ScrapeConfig(url=url, **BASE_CONFIG))
    media = _extract_xig_polaris_media(result.content)
    if not media:
        raise ValueError(f"Could not find post data in page: {url}")
    return parse_post(media)



def parse_user_posts(data: Dict) -> Dict:
    """Reduce users posts' dataset to the most important fields"""
    result = jmespath.search(
        """{
        id: id,
        shortcode: code,
        caption: caption,
        taken_at: taken_at,
        video_versions: video_versions,
        image_versions2: image_versions2,
        original_height: original_height,
        original_width: original_width,
        link: link,
        title: title,
        comment_count: comment_count,
        top_likers: top_likers,
        like_count: like_count,
        usertags: usertags,
        clips_metadata: clips_metadata,
        comments: comments
    }""",
        data,
    )

    return result


async def scrape_user_posts(username: str, page_size=12, max_pages: Optional[int] = None):
    """Scrape all posts of an instagram user of given the username"""
    base_url = "https://www.instagram.com/graphql/query/"
    variables = {
        "after": None,
        "before": None,
        "data": {
            "count": page_size,
            "include_reel_media_seen_timestamp": True,
            "include_relationship_info": True,
            "latest_besties_reel_media": True,
            "latest_reel_media": True
        },
        "first": page_size,
        "last": None,
        "username": f"{username}",
        "__relay_internal__pv__PolarisIsLoggedInrelayprovider": True,
        "__relay_internal__pv__PolarisShareSheetV3relayprovider": True
    }

    prev_cursor = None
    _page_number = 1

    while True:
        body = f"variables={json.dumps(variables, separators=(',', ':'))}&doc_id={INSTAGRAM_ACCOUNT_DOCUMENT_ID}"
        params = {
            "doc_id": INSTAGRAM_ACCOUNT_DOCUMENT_ID,  # e.g., "7950326061742207"
            "variables": json.dumps(variables, separators=(",", ":"))
        }

        # Build the final URL by appending the query string to the base URL
        final_url = f"{base_url}?{urlencode(params)}"
        result = await SCRAPFLY.async_scrape(ScrapeConfig(
            final_url, **BASE_CONFIG, method="GET",
            headers={"content-type": "application/x-www-form-urlencoded"},
        ))

        data = json.loads(result.content)
        
        posts = data["data"]["xdt_api__v1__feed__user_timeline_graphql_connection"]
        for post in posts["edges"]:
            yield parse_user_posts(post["node"])

        page_info = posts["page_info"]
        if not page_info["has_next_page"]:
            log.info(f"scraping posts page {_page_number}")
            break

        if page_info["end_cursor"] == prev_cursor:
            log.warning("found no new posts, breaking")
            break

        prev_cursor = page_info["end_cursor"] 
        variables["after"] = page_info["end_cursor"]
        _page_number += 1

        if max_pages and _page_number > max_pages:
            break

def parse_post_comment(data: Dict) -> Dict:
    """refine the comment dataset"""
    return jmespath.search(
        """{
        id: pk,
        text: text,
        created_at: created_at,
        owner: user.username,
        owner_id: user.id,
        owner_verified: user.is_verified,
        owner_profile_pic: user.profile_pic_url,
        likes: comment_like_count
    }""",
        data,
    )


async def scrape_post_comments(url: str):
    """Scrape comments from an Instagram post"""
    log.info("scraping instagram post comments: {}", url)

    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=url,
            render_js=True,
            proxy_pool="public_residential_pool",
            js_scenario=COMMENTS_JS_SCENARIO,
            **BASE_CONFIG,
        )
    )

    comments = []
    seen_ids = set()
    xhr_calls = result.scrape_result.get("browser_data", {}).get("xhr_call") or []
    for xhr in xhr_calls:
        body = (xhr.get("response") or {}).get("body")
        if not body or "comments_connection" not in body:
            continue
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            log.warning("no JSON comments found, skipping")
            continue

        edges = jmespath.search(
            "data.xig_polaris_media.comments_connection.edges[].node", data
        ) or []
        for node in edges:
            if node["id"] in seen_ids:
                continue
            seen_ids.add(node["id"])
            comments.append(parse_post_comment(node))

    log.success("scraped {} comments", len(comments))
    return comments