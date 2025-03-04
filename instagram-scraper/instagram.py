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


def parse_post(data: Dict) -> Dict:
    """Reduce post dataset to the most important fields"""
    log.debug("parsing post data {}", data["shortcode"])
    result = jmespath.search(
        """{
        id: id,
        shortcode: shortcode,
        dimensions: dimensions,
        src: display_url,
        thumbnail_src: thumbnail_src,
        media_preview: media_preview,
        video_url: video_url,
        views: video_view_count,
        likes: edge_media_preview_like.count,
        location: location.name,
        taken_at: taken_at_timestamp,
        related: edge_web_media_to_related_media.edges[].node.shortcode,
        type: product_type,
        video_duration: video_duration,
        music: clips_music_attribution_info,
        is_video: is_video,
        tagged_users: edge_media_to_tagged_user.edges[].node.user.username,
        captions: edge_media_to_caption.edges[].node.text,
        related_profiles: edge_related_profiles.edges[].node.username
    }""",
        data,
    )
    comments_data = parse_comments(data)
    result.update(comments_data)

    return result


async def scrape_post(url_or_shortcode: str) -> Dict:
    """Scrape single Instagram post data"""
    if "http" in url_or_shortcode:
        shortcode = url_or_shortcode.split("/p/")[-1].split("/")[0]
    else:
        shortcode = url_or_shortcode
    log.info("scraping instagram post: {}", shortcode)
    variables = json.dumps({
        'shortcode':shortcode,'fetch_tagged_user_count':None,
        'hoisted_comment_id':None,'hoisted_reply_id':None
    }, separators=(',', ':'))
    body = f"variables={variables}&doc_id={INSTAGRAM_DOCUMENT_ID}"
    url = "https://www.instagram.com/graphql/query"
    result = await SCRAPFLY.async_scrape(
        ScrapeConfig(
            url=url,
            method="POST",
            body=body,
           headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            **BASE_CONFIG
        )
    )

    data = json.loads(result.content)
    return parse_post(data["data"]["xdt_shortcode_media"])


def parse_user_posts(data: Dict) -> Dict:
    """Reduce users posts' dataset to the most important fields"""
    log.debug("parsing post data {}", data["code"])
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
        
        with open("ts2.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
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