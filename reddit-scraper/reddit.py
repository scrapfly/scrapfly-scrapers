"""
This is an example web scraper for Reddit.com.

To run this scraper set env variable $SCRAPFLY_KEY with your scrapfly API key:
$ export $SCRAPFLY_KEY="your key from https://scrapfly.io/dashboard"
"""

import os
from typing import Dict, List, Union
from datetime import datetime
from loguru import logger as log
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

SCRAPFLY = ScrapflyClient(key=os.environ["SCRAPFLY_KEY"])

BASE_CONFIG = {
    # enable the anti scraping protection
    "asp": True,
    # set the proxy country to US
    "country": "US",
    # bypassing reddit requires emabling JavaScript and using the residential proxy pool
    "render_js": True,
    "proxy_pool": "public_residential_pool"
}

def parse_subreddit(response: ScrapeApiResponse) -> Dict:
    """parse article data from HTML"""
    selector = response.selector
    url = response.context["url"]
    info = {}
    info["id"] = url.split("/r")[-1].replace("/", "")
    info["description"] = selector.xpath("//shreddit-subreddit-header/@description").get()
    members = selector.xpath("//shreddit-subreddit-header/@subscribers").get()
    rank = selector.xpath("//strong[@id='position']/text()").get()
    info["rank"] = rank.strip() if rank else None
    info["members"] = int(members) if members else None
    info["bookmarks"] = {}
    for item in selector.xpath("//div[faceplate-tracker[@source='community_menu']]/faceplate-tracker"):
        name = item.xpath(".//a/span/span/span/text()").get()
        link = item.xpath(".//a/@href").get()
        info["bookmarks"][name] = link

    info["url"] = url
    post_data = []
    for box in selector.xpath("//article"):
        link = box.xpath(".//a/@href").get()
        author = box.xpath(".//shreddit-post/@author").get()
        post_label = box.xpath(".//faceplate-tracker[@source='post']/a/span/div/text()").get()
        upvotes = box.xpath(".//shreddit-post/@score").get()
        comment_count = box.xpath(".//shreddit-post/@comment-count").get()
        attachment_type = box.xpath(".//shreddit-post/@post-type").get()
        if attachment_type and attachment_type == "image":
            attachment_link = box.xpath(".//div[contains(@class, 'img')]/*/@src").get()
        elif attachment_type == "video":
            attachment_link = box.xpath(".//shreddit-player/@preview").get()
        else:
            attachment_link = None
        post_data.append({
            "authorProfile": "https://www.reddit.com/user/" + author if author else None,
            "authorId": box.xpath(".//shreddit-post/@author-id").get(),            
            "title": box.xpath("./@aria-label").get(),
            "link": "https://www.reddit.com" + link if link else None,
            "publishingDate": box.xpath(".//shreddit-post/@created-timestamp").get(),
            "postId": box.xpath(".//shreddit-post/@id").get(),
            "postLabel": post_label.strip() if post_label else None,
            "postUpvotes": int(upvotes) if upvotes else None,
            "commentCount": int(comment_count) if comment_count else None,
            "attachmentType": attachment_type,
            "attachmentLink": attachment_link,
        })
    # id for the next posts batch
    cursor_id = selector.xpath("//shreddit-post/@more-posts-cursor").get()
    return {"post_data": post_data, "info": info, "cursor": cursor_id}


async def scrape_subreddit(subreddit_id: str, max_pages: int = None) -> Dict:
    """scrape articles on a subreddit"""
    base_url = f"https://www.reddit.com/r/{subreddit_id}/"
    response = await SCRAPFLY.async_scrape(ScrapeConfig(base_url, **BASE_CONFIG))
    subreddit_data = {}
    data = parse_subreddit(response)
    subreddit_data["info"] = data["info"]
    subreddit_data["posts"] = data["post_data"]
    cursor = data["cursor"]

    def make_pagination_url(cursor_id: str):
        return f"https://www.reddit.com/svc/shreddit/community-more-posts/hot/?after={cursor_id}%3D%3D&t=DAY&name=wallstreetbets&feedLength=3" 
        
    while cursor and (max_pages is None or max_pages > 0):
        url = make_pagination_url(cursor)
        response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
        data = parse_subreddit(response)
        cursor = data["cursor"]

        post_data = data["post_data"]
        subreddit_data["posts"].extend(post_data)
        if max_pages is not None:
            max_pages -= 1
    log.success(f"scraped {len(subreddit_data['posts'])} posts from the rubreddit: r/{subreddit_id}")
    return subreddit_data


def parse_post_info(response: ScrapeApiResponse) -> Dict:
    """parse post data from a subreddit post"""
    selector = response.selector
    info = {}
    label = selector.xpath("//faceplate-tracker[@source='post']/a/span/div/text()").get()
    comments = selector.xpath("//shreddit-post/@comment-count").get()
    upvotes = selector.xpath("//shreddit-post/@score").get()
    info["authorId"] = selector.xpath("//shreddit-post/@author-id").get()
    info["author"] = selector.xpath("//shreddit-post/@author").get()
    info["authorProfile"] = "https://www.reddit.com/user/" + info["author"] if info["author"] else None
    info["subreddit"] = selector.xpath("//shreddit-post/@subreddit-prefixed-name").get().replace("r/", "")
    info["postId"] = selector.xpath("//shreddit-post/@id").get()
    info["postLabel"] = label.strip() if label else None
    info["publishingDate"] = selector.xpath("//shreddit-post/@created-timestamp").get()
    info["postTitle"] = selector.xpath("//shreddit-post/@post-title").get()
    info["postLink"] = selector.xpath("//shreddit-canonical-url-updater/@value").get()
    info["commentCount"] = int(comments) if comments else None
    info["upvoteCount"] = int(upvotes) if upvotes else None
    info["attachmentType"] = selector.xpath("//shreddit-post/@post-type").get()
    info["attachmentLink"] = selector.xpath("//shreddit-post/@content-href").get()
    return info


def parse_post_comments(response: ScrapeApiResponse) -> List[Dict]:
    """parse post comments"""

    def parse_comment(parent_selector) -> Dict:
        """parse a comment object"""
        author = parent_selector.xpath("./@data-author").get()
        link = parent_selector.xpath("./@data-permalink").get()
        dislikes = parent_selector.xpath(".//span[contains(@class, 'dislikes')]/@title").get()
        upvotes = parent_selector.xpath(".//span[contains(@class, 'likes')]/@title").get()
        downvotes = parent_selector.xpath(".//span[contains(@class, 'unvoted')]/@title").get()        
        return {
            "authorId": parent_selector.xpath("./@data-author-fullname").get(),
            "author": author,
            "authorProfile": "https://www.reddit.com/user/" + author if author else None,
            "commentId": parent_selector.xpath("./@data-fullname").get(),
            "link": "https://www.reddit.com" + link if link else None,
            "publishingDate": parent_selector.xpath(".//time/@datetime").get(),
            "commentBody": parent_selector.xpath(".//div[@class='md']/p/text()").get(),
            "upvotes": int(upvotes) if upvotes else None,
            "dislikes": int(dislikes) if dislikes else None,
            "downvotes": int(downvotes) if downvotes else None,            
        }

    def parse_replies(what) -> List[Dict]:
        """recursively parse replies"""
        replies = []
        for reply_box in what.xpath(".//div[@data-type='comment']"):
            reply_comment = parse_comment(reply_box)
            child_replies = parse_replies(reply_box)
            if child_replies:
                reply_comment["replies"] = child_replies
            replies.append(reply_comment)
        return replies

    selector = response.selector
    data = []
    for item in selector.xpath("//div[@class='sitetable nestedlisting']/div[@data-type='comment']"):
        comment_data = parse_comment(item)
        replies = parse_replies(item)
        if replies:
            comment_data["replies"] = replies
        data.append(comment_data)            
    return data


async def scrape_post(url: str, sort: Union["old", "new", "top"]) -> Dict:
    """scrape eubreddit post and comment data"""
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    post_data = {}
    post_data["info"] = parse_post_info(response)
    # scrape the comments from the old.reddit version, with the same post URL
    # click the load more button on the page to retrieve another results    
    bulk_comments_page_url = post_data["info"]["postLink"].replace("www", "old") + f"?sort={sort}&limit=500"
    response = await SCRAPFLY.async_scrape(ScrapeConfig(bulk_comments_page_url, **BASE_CONFIG))
    post_data["comments"] = parse_post_comments(response) 
    log.success(f"scraped {len(post_data['comments'])} comments from the post {url}")
    return post_data


def parse_user_posts(response: ScrapeApiResponse) -> List[Dict]:
    """parse user posts from user profiles"""
    selector = response.selector
    data = []
    for box in selector.xpath("//div[@id='siteTable']/div[contains(@class, 'thing')]"):
        author = box.xpath("./@data-author").get()
        link = box.xpath("./@data-permalink").get()
        publishing_date = box.xpath("./@data-timestamp").get()
        publishing_date = datetime.fromtimestamp(int(publishing_date) / 1000.0).strftime('%Y-%m-%dT%H:%M:%S.%f%z') if publishing_date else None
        comment_count = box.xpath("./@data-comments-count").get()
        post_score = box.xpath("./@data-score").get() 
        data.append({
            "authorId": box.xpath("./@data-author-fullname").get(),
            "author": author,
            "authorProfile": "https://www.reddit.com/user/" + author if author else None,
            "postId": box.xpath("./@data-fullname").get(),
            "postLink": "https://www.reddit.com" + link if link else None,
            "postTitle": box.xpath(".//p[@class='title']/a/text()").get(),
            "postSubreddit": box.xpath("./@data-subreddit-prefixed").get(),
            "publishingDate": publishing_date,
            "commentCount": int(comment_count) if comment_count else None,
            "postScore": int(post_score) if post_score else None,
            "attachmentType": box.xpath("./@data-type").get(),
            "attachmentLink": box.xpath("./@data-url").get(),
        })
    next_page_url = selector.xpath("//span[@class='next-button']/a/@href").get()
    return {"data": data, "url": next_page_url}


async def scrape_user_posts(username: str, sort: Union["new", "top", "controversial"], max_pages: int = None) -> List[Dict]:
    """scrape user posts"""
    url = f"https://old.reddit.com/user/{username}/submitted/?sort={sort}"
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_user_posts(response)
    post_data, next_page_url = data["data"], data["url"]

    while next_page_url and (max_pages is None or max_pages > 0):
        response = await SCRAPFLY.async_scrape(ScrapeConfig(next_page_url, **BASE_CONFIG))
        data = parse_user_posts(response)
        next_page_url = data["url"]
        post_data.extend(data["data"])
        if max_pages is not None:
            max_pages -= 1
    log.success(f"scraped {len(post_data)} posts from the {username} reddit profile")
    return post_data


def parse_user_comments(response: ScrapeApiResponse) -> List[Dict]:
    """parse user posts from user profiles"""
    selector = response.selector
    data = []
    for box in selector.xpath("//div[@id='siteTable']/div[contains(@class, 'thing')]"):
        author = box.xpath("./@data-author").get()
        link = box.xpath("./@data-permalink").get()
        dislikes = box.xpath(".//span[contains(@class, 'dislikes')]/@title").get()
        upvotes = box.xpath(".//span[contains(@class, 'likes')]/@title").get()
        downvotes = box.xpath(".//span[contains(@class, 'unvoted')]/@title").get()
        data.append({
            "authorId": box.xpath("./@data-author-fullname").get(),
            "author": author,
            "authorProfile": "https://www.reddit.com/user/" + author if author else None,
            "commentId": box.xpath("./@data-fullname").get(),
            "commentLink": "https://www.reddit.com" + link if link else None,
            "commentBody": "".join(box.xpath(".//div[contains(@class, 'usertext-body')]/div/p/text()").getall()).replace("\n", ""),
            "attachedCommentLinks": box.xpath(".//div[contains(@class, 'usertext-body')]/div/p/a/@href").getall(),
            "publishingDate": box.xpath(".//time/@datetime").get(),
            "dislikes": int(dislikes) if dislikes else None,
            "upvotes": int(upvotes) if upvotes else None,
            "downvotes": int(downvotes) if downvotes else None,
            "replyTo": {
                "postTitle": box.xpath(".//p[@class='parent']/a[@class='title']/text()").get(),
                "postLink": "https://www.reddit.com" + box.xpath(".//p[@class='parent']/a[@class='title']/@href").get(),
                "postAuthor": box.xpath(".//p[@class='parent']/a[contains(@class, 'author')]/text()").get(),
                "postSubreddit": box.xpath("./@data-subreddit-prefixed").get(),    
            }
        })
    next_page_url = selector.xpath("//span[@class='next-button']/a/@href").get()
    return {"data": data, "url": next_page_url}


async def scrape_user_comments(username: str, sort: Union["new", "top", "controversial"], max_pages: int = None) -> List[Dict]:
    """scrape user posts"""
    url = f"https://old.reddit.com/user/{username}/comments/?sort={sort}"
    response = await SCRAPFLY.async_scrape(ScrapeConfig(url, **BASE_CONFIG))
    data = parse_user_comments(response)
    post_data, next_page_url = data["data"], data["url"]

    while next_page_url and (max_pages is None or max_pages > 0):
        response = await SCRAPFLY.async_scrape(ScrapeConfig(next_page_url, **BASE_CONFIG))
        data = parse_user_comments(response)
        next_page_url = data["url"]
        post_data.extend(data["data"])
        if max_pages is not None:
            max_pages -= 1
    log.success(f"scraped {len(post_data)} posts from the {username} reddit profile")
    return post_data
