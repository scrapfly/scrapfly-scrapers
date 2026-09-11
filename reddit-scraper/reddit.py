"""
This is an example web scraper for Reddit.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
import re
from typing import Callable, Dict, List, Literal, Optional
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # enable the anti scraping protection
    "asp": True,
    # set the proxy country to US
    "country": "US",
    # bypassing reddit requires enabling JavaScript and using the residential proxy pool
    "render_js": True,
    "proxy_pool": "public_residential_pool",
}

REDDIT_URL = "https://www.reddit.com"


def absolute_url(path: Optional[str]) -> Optional[str]:
    """turn a reddit path into an absolute URL"""
    if not path:
        return None
    if path.startswith("http"):
        return path
    return REDDIT_URL + path if path.startswith("/") else f"{REDDIT_URL}/{path}"


def to_int(value) -> Optional[int]:
    """parse an integer attribute, or None when missing"""
    return int(value) if value else None


def parse_score(node) -> Optional[int]:
    """parse score from @score or the rendered vote button faceplate-number"""
    score = (
        node.xpath("./@score").get()
        or node.xpath(".//shreddit-comment-action-row/@score").get()
        or node.xpath(".//span[contains(@class, 'rpl-vote-button-group')]//faceplate-number/@number").get()
        or node.xpath(".//button[@upvote]/following-sibling::span[1]//faceplate-number/@number").get()
    )
    return to_int(score)


def profile_url(author: Optional[str]) -> Optional[str]:
    """build a reddit user profile URL"""
    return f"{REDDIT_URL}/user/{author}" if author else None


def comment_text(node) -> Optional[str]:
    """join paragraph text from a shreddit comment body"""
    parts = node.xpath(".//div[contains(@id, 'rtjson-content')]//p//text()").getall()
    text = "".join(parts).strip()
    return text or None


def parse_attachment(post) -> tuple:
    """parse post attachment type and the best available media/content URL"""
    attachment_type = post.xpath("./@post-type").get()
    attachment_link = (
        post.xpath(".//img[contains(@class, 'media-lightbox-img')]/@src").get()
        or post.xpath(".//shreddit-player/@preview").get()
        or post.xpath("./@content-href").get()
    )
    return attachment_type, absolute_url(attachment_link)


def next_profile_page_url(selector) -> Optional[str]:
    """extract the next profile pagination URL from a faceplate-partial cursor link"""
    partial = selector.xpath("//faceplate-partial[contains(@src, '-more-posts')]/@src").get()
    return absolute_url(partial)


async def scrape_paginated(
    url: str,
    parse: Callable[[ScrapeApiResponse], list],
    wait_for_selector: str = None,
    max_pages: int = None,
) -> list:
    """scrape a first page then follow faceplate-partial pagination"""
    config = {**BASE_CONFIG}
    if wait_for_selector:
        config["wait_for_selector"] = wait_for_selector
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **config))
    data = parse(response)
    next_url = next_profile_page_url(response.selector)

    while next_url and (max_pages is None or max_pages > 0):
        response = await SCRAPFLY.async_scrape(ScrapeConfig(next_url, **BASE_CONFIG))
        data.extend(parse(response))
        next_url = next_profile_page_url(response.selector)
        if max_pages is not None:
            max_pages -= 1
    return data


def parse_subreddit(response: ScrapeApiResponse) -> Dict:
    """parse subreddit info and post cards from HTML"""
    selector = response.selector
    url = response.context["url"]
    members = selector.xpath("//faceplate-number[following-sibling::text()[contains(., 'members')]]/@number").get()
    weekly_active = selector.xpath("//shreddit-subreddit-header/@weekly-active-users").get()
    rank = selector.xpath("//strong[@id='position']/text()").get()

    bookmarks = {}
    for item in selector.xpath("//div[faceplate-tracker[@source='community_menu']]/faceplate-tracker"):
        name = item.xpath(".//a/span/span/span/text()").get()
        link = item.xpath(".//a/@href").get()
        if name and link:
            bookmarks[name] = link

    posts = []
    for article in selector.xpath("//article[@data-post-id]"):
        post = article.xpath(".//shreddit-post")
        if not post:
            continue
        post = post[0]
        author = post.xpath("./@author").get()
        label = article.xpath(".//span[contains(@class, 'bg-tone-4')]/div/text()").get()
        attachment_type, attachment_link = parse_attachment(post)
        posts.append(
            {
                "authorProfile": profile_url(author),
                "authorId": post.xpath("./@author-id").get(),
                "title": post.xpath("./@post-title").get(),
                "link": absolute_url(article.xpath(".//a/@href").get()),
                "publishingDate": post.xpath("./@created-timestamp").get(),
                "postId": post.xpath("./@id").get(),
                "postLabel": label.strip() if label else None,
                "postUpvotes": to_int(post.xpath("./@score").get()),
                "commentCount": to_int(post.xpath("./@comment-count").get()),
                "attachmentType": attachment_type,
                "attachmentLink": attachment_link,
            }
        )

    return {
        "info": {
            "id": url.split("/r")[-1].replace("/", ""),
            "description": selector.xpath("//shreddit-subreddit-header/@description").get(),
            "rank": rank.strip() if rank else None,
            "members": to_int(members) if members else to_int(weekly_active),
            "bookmarks": bookmarks,
            "url": url,
        },
        "post_data": posts,
        "cursor": selector.xpath("//shreddit-post/@more-posts-cursor").get(),
    }


async def scrape_subreddit(subreddit_id: str, max_pages: int = None) -> Dict:
    """scrape posts from a subreddit"""
    log.info("scraping subreddit r/{}", subreddit_id)
    url = f"{REDDIT_URL}/r/{subreddit_id}/"
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, **BASE_CONFIG, wait_for_selector="//article[@data-post-id]")
    )
    data = parse_subreddit(response)
    subreddit_data = {"info": data["info"], "posts": data["post_data"]}
    cursor = data["cursor"]

    while cursor and (max_pages is None or max_pages > 0):
        page_url = (
            f"{REDDIT_URL}/svc/shreddit/community-more-posts/hot/"
            f"?after={cursor}%3D%3D&t=DAY&name={subreddit_id}&feedLength=3"
        )
        response = await SCRAPFLY.async_scrape(ScrapeConfig(page_url, **BASE_CONFIG))
        data = parse_subreddit(response)
        cursor = data["cursor"]
        subreddit_data["posts"].extend(data["post_data"])
        if max_pages is not None:
            max_pages -= 1

    log.success(f"scraped {len(subreddit_data['posts'])} posts from the subreddit: r/{subreddit_id}")
    return subreddit_data


def parse_post_info(response: ScrapeApiResponse) -> Dict:
    """parse post data from a subreddit post page"""
    selector = response.selector
    author = selector.xpath("//shreddit-post/@author").get()
    label = selector.xpath("//faceplate-tracker[@source='post']/a/span/div/text()").get()
    subreddit = selector.xpath("//shreddit-post/@subreddit-prefixed-name").get()
    return {
        "authorId": selector.xpath("//shreddit-post/@author-id").get(),
        "author": author,
        "authorProfile": profile_url(author),
        "subreddit": subreddit.replace("r/", "") if subreddit else None,
        "postId": selector.xpath("//shreddit-post/@id").get(),
        "postLabel": label.strip() if label else None,
        "publishingDate": selector.xpath("//shreddit-post/@created-timestamp").get(),
        "postTitle": selector.xpath("//shreddit-post/@post-title").get(),
        "postLink": absolute_url(selector.xpath("//shreddit-post/@permalink").get()),
        "commentCount": to_int(selector.xpath("//shreddit-post/@comment-count").get()),
        "upvoteCount": to_int(selector.xpath("//shreddit-post/@score").get()),
        "attachmentType": selector.xpath("//shreddit-post/@post-type").get(),
        "attachmentLink": selector.xpath("//shreddit-post/@content-href").get(),
    }


def parse_post_comments(response: ScrapeApiResponse) -> List[Dict]:
    """parse post comments from shreddit-comment elements, rebuilding the reply tree"""
    comments = {}
    parent_ids = {}
    order = []
    for node in response.selector.xpath("//shreddit-comment"):
        thing_id = node.xpath("./@thingid").get()
        if not thing_id or thing_id in comments:
            continue
        author = node.xpath("./@author").get()
        if author == "[deleted]":
            author = None
        comments[thing_id] = {
            "authorId": node.xpath("./@author-id").get() or node.xpath(".//shreddit-overflow-menu/@author-id").get(),
            "author": author,
            "authorProfile": profile_url(author),
            "commentId": thing_id,
            "link": absolute_url(node.xpath("./@permalink").get()),
            "publishingDate": node.xpath("./@created").get(),
            "commentBody": comment_text(node),
            "upvotes": parse_score(node),
        }
        parent_ids[thing_id] = node.xpath("./@parentid").get()
        order.append(thing_id)

    top_level = []
    for thing_id in order:
        comment = comments[thing_id]
        parent_id = parent_ids[thing_id]
        if parent_id and parent_id in comments:
            comments[parent_id].setdefault("replies", []).append(comment)
        else:
            top_level.append(comment)
    return top_level


async def scrape_post_comments(subreddit: str, post_id: str, sort: str) -> List[Dict]:
    """fetch and parse one sort's worth of comments via the shreddit comments endpoint"""
    url = f"{REDDIT_URL}/svc/shreddit/comments/r/{subreddit}/{post_id}?sort={sort}"
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    return parse_post_comments(response)


async def scrape_post(url: str, sort: Literal["old", "new", "top"]) -> Dict:
    """scrape subreddit post and comment data"""
    log.info("scraping post {}", url)
    response = await SCRAPFLY.async_scrape(
        ScrapeConfig(url, **BASE_CONFIG, wait_for_selector="//shreddit-post")
    )
    post_data = {"info": parse_post_info(response)}
    comments_by_id = {}
    for comment_sort in dict.fromkeys([sort, "top", "new", "old"]):
        for comment in await scrape_post_comments(
            post_data["info"]["subreddit"], post_data["info"]["postId"], comment_sort
        ):
            comments_by_id.setdefault(comment["commentId"], comment)
    post_data["comments"] = list(comments_by_id.values())
    log.success(f"scraped {len(post_data['comments'])} comments from the post {url}")
    return post_data


def parse_user_posts(response: ScrapeApiResponse) -> List[Dict]:
    """parse user posts from a profile page or its pagination partial"""
    data = []
    for post in response.selector.xpath("//shreddit-post"):
        author = post.xpath("./@author").get()
        attachment_type, attachment_link = parse_attachment(post)
        data.append(
            {
                "authorId": post.xpath("./@author-id").get(),
                "author": author,
                "authorProfile": profile_url(author),
                "postId": post.xpath("./@id").get(),
                "postLink": absolute_url(post.xpath("./@permalink").get()),
                "postTitle": post.xpath("./@post-title").get(),
                "postSubreddit": post.xpath("./@subreddit-prefixed-name").get(),
                "publishingDate": post.xpath("./@created-timestamp").get(),
                "commentCount": to_int(post.xpath("./@comment-count").get()),
                "postScore": to_int(post.xpath("./@score").get()),
                "attachmentType": attachment_type,
                "attachmentLink": attachment_link,
            }
        )
    return data


async def scrape_user_posts(
    username: str, sort: Literal["new", "top", "controversial"], max_pages: int = None
) -> List[Dict]:
    """scrape user posts"""
    log.info("scraping posts from user {}", username)
    url = f"{REDDIT_URL}/user/{username}/submitted/?sort={sort}"
    post_data = await scrape_paginated(
        url, parse_user_posts, wait_for_selector="//shreddit-post", max_pages=max_pages
    )
    log.success(f"scraped {len(post_data)} posts from the {username} reddit profile")
    return post_data


def parse_user_comments(response: ScrapeApiResponse, username: str) -> List[Dict]:
    """parse user comments from a profile page or its pagination partial"""
    data = []
    for box in response.selector.xpath("//shreddit-profile-comment"):
        href = box.xpath("./@href").get()
        author = box.xpath(".//shreddit-overflow-menu/@author-name").get() or username
        post_title = "".join(box.xpath(".//h2//a//text()").getall()).strip()
        post_link = box.xpath(".//h2//a/@href").get()
        subreddit_match = re.match(r"^(/r/[^/]+)/", href or "")
        data.append(
            {
                "authorId": box.xpath(".//shreddit-overflow-menu/@author-id").get(),
                "author": author,
                "authorProfile": profile_url(author),
                "commentId": box.xpath("./@comment-id").get(),
                "commentLink": absolute_url(href),
                "commentBody": comment_text(box),
                "attachedCommentLinks": [
                    link
                    for link in box.xpath(".//div[contains(@id, 'rtjson-content')]//a/@href").getall()
                    if link and "reddit.com" not in link
                ],
                "publishingDate": box.xpath(".//faceplate-timeago/@ts").get(),
                "upvotes": parse_score(box),
                "replyTo": {
                    "postTitle": post_title or None,
                    "postLink": absolute_url(post_link),
                    "postSubreddit": subreddit_match.group(1).lstrip("/") if subreddit_match else None,
                },
            }
        )
    return data


async def scrape_user_comments(
    username: str, sort: Literal["new", "top", "controversial"], max_pages: int = None
) -> List[Dict]:
    """scrape user comments"""
    log.info("scraping comments from user {}", username)
    url = f"{REDDIT_URL}/user/{username}/comments/?sort={sort}"
    comment_data = await scrape_paginated(
        url,
        lambda response: parse_user_comments(response, username),
        wait_for_selector="//shreddit-profile-comment",
        max_pages=max_pages,
    )
    log.success(f"scraped {len(comment_data)} comments from the {username} reddit profile")
    return comment_data
