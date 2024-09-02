from cerberus import Validator as _Validator
import pytest
import reddit
import pprint

pp = pprint.PrettyPrinter(indent=4)


class Validator(_Validator):
    def _validate_min_presence(self, min_presence, field, value):
        pass  # required for adding non-standard keys to schema


def validate_or_fail(item, validator):
    if not validator.validate(item):
        pp.pformat(item)
        pytest.fail(f"Validation failed for item: {pp.pformat(item)}\nErrors: {validator.errors}")


def require_min_presence(items, key, min_perc=0.1):
    """check whether dataset contains items with some amount of non-null values for a given key"""
    count = sum(1 for item in items if item.get(key))
    if count < len(items) * min_perc:
        pytest.fail(
            f'inadequate presence of "{key}" field in dataset, only {count} out of {len(items)} items have it (expected {min_perc*100}%)'
        )



post_schema = {
    "info": {
        "type": "dict",
        "schema": {
            "authorId": {"type": "string"},
            "author": {"type": "string"},
            "authorProfile": {"type": "string"},
            "subreddit": {"type": "string"},
            "postId": {"type": "string"},
            "postLabel": {"type": "string"},
            "publishingDate": {"type": "string"},
            "postTitle": {"type": "string"},
            "postLink": {"type": "string"},
            "commentCount": {"type": "integer"},
            "upvoteCount": {"type": "integer"},
            "attachmentType": {"type": "string"},
            "attachmentLink": {"type": "string", "nullable": True},
        }
    },
    "comments": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "authorId": {"type": "string", "nullable": True},
                "author": {"type": "string", "nullable": True},
                "authorProfile": {"type": "string", "nullable": True},
                "commentId": {"type": "string"},
                "link": {"type": "string"},
                "publishingDate": {"type": "string"},
                "commentBody": {"type": "string", "nullable": True},
                "upvotes": {"type": "integer"},
                "dislikes": {"type": "integer"},
                "downvotes": {"type": "integer"},
            }
        }
    }
}

subreddit_schema = {
    "info": {
        "type": "dict",
        "schema": {
            "id": {"type": "string"},
            "description": {"type": "string"},
            "members": {"type": "integer"},
            "rank": {"type": "string"},
            "bookmarks": {
                "type": "dict",
                "schema": {
                    "Wiki": {"type": "string"},
                    "YouTube": {"type": "string"},
                    "Discord": {"type": "string"},
                    "Twitch": {"type": "string"},
                }
            },
            "url": {"type": "string"}
        }
    },
    "posts": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "authorProfile": {"type": "string"},
                "authorId": {"type": "string", "nullable": True}, # deleted profiles
                "title": {"type": "string"},
                "link": {"type": "string"},
                "publishingDate": {"type": "string"},
                "postId": {"type": "string"},
                "postLabel": {"type": "string", "nullable": True},
                "postUpvotes": {"type": "integer"},
                "commentCount": {"type": "integer"},
                "attachmentType": {"type": "string"},
                "attachmentLink": {"type": "string", "nullable": True},
            }
        }
    }
}

user_post_schema = {
    "authorId": {"type": "string"},
    "author": {"type": "string"},
    "authorProfile": {"type": "string"},
    "postId": {"type": "string"},
    "postLink": {"type": "string"},
    "postTitle": {"type": "string"},
    "postSubreddit": {"type": "string"},
    "publishingDate": {"type": "string"},
    "commentCount": {"type": "integer"},
    "postScore": {"type": "integer"},
    "attachmentType": {"type": "string"},
    "attachmentLink": {"type": "string", "nullable": True}
}

user_comment_schema = {
    "authorId": {"type": "string"},
    "author": {"type": "string"},
    "authorProfile": {"type": "string"},
    "commentId": {"type": "string"},
    "commentLink": {"type": "string"},
    "commentBody": {"type": "string", "nullable": True},
    "attachedCommentLinks": {
        "type": "list",
        "schema": {"type": "string"}
    },
    "dislikes": {"type": "integer"},
    "upvotes": {"type": "integer"},
    "downvotes": {"type": "integer"},
    "replyTo": {
        "type": "dict",
        "schema": {
            "postTitle": {"type": "string"},
            "postLink": {"type": "string"},
            "postAuthor": {"type": "string"},
            "postSubreddit": {"type": "string"}
        }
    }
}


@pytest.mark.asyncio
async def test_subreddit_scraping():
    subreddit_data = await reddit.scrape_subreddit(
        subreddit_id="wallstreetbets",
        max_pages=3
    )
    validator = Validator(subreddit_schema, allow_unknown=True)
    validate_or_fail(subreddit_data, validator)
    data = []
    data.append(subreddit_data)
    for k in subreddit_schema:
        require_min_presence(data, k, min_perc=subreddit_schema[k].get("min_presence", 0.1))

    assert len(subreddit_data["posts"]) >= 50


@pytest.mark.asyncio
async def test_post_scraping():
    post_data = await reddit.scrape_post(
        url="https://www.reddit.com/r/wallstreetbets/comments/1c4vwlp/what_are_your_moves_tomorrow_april_16_2024/",
        sort="top",        
    )
    validator = Validator(post_schema, allow_unknown=True)
    validate_or_fail(post_data, validator)
    data = []
    data.append(post_data)    
    for k in post_schema:
        require_min_presence(data, k, min_perc=post_schema[k].get("min_presence", 0.1))    

    assert len(post_data["comments"]) >= 50


@pytest.mark.asyncio
async def test_user_post_scraping():
    user_post_data = await reddit.scrape_user_posts(
        username="Scrapfly",
        sort="top",
        max_pages=3
    )
    validator = Validator(user_post_schema, allow_unknown=True)
    for item in user_post_data:
        validate_or_fail(item, validator)

    for k in user_post_schema:
        require_min_presence(user_post_data, k, min_perc=user_post_schema[k].get("min_presence", 0.05))    

    assert len(user_post_data) >= 25


@pytest.mark.asyncio
async def test_user_comment_scraping():
    user_comment_data = await reddit.scrape_user_comments(
        username="Scrapfly",
        sort="top",
        max_pages=3
    )
    validator = Validator(user_comment_schema, allow_unknown=True)
    for item in user_comment_data:
        validate_or_fail(item, validator)

    for k in user_comment_schema:
        require_min_presence(user_comment_data, k, min_perc=user_comment_schema[k].get("min_presence", 0.05))  

    assert len(user_comment_data) >= 2