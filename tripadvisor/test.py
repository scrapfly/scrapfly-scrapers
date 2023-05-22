import json
from pathlib import Path
from cerberus import Validator

result_fp = Path(__file__).parent.joinpath("results/hotels.json").absolute()
hotel_data = json.loads(result_fp.read_text())


def test_hotels():
    assert len(hotel_data["price"]) > 10


def test_info():
    schema = {
        "name": {"type": "string", "required": True},
        "id": {"type": "integer", "required": True},
        "type": {"type": "string", "required": True, "allowed": ["T_HOTEL"]},
        "description": {"type": "string", "required": True},
        "rating": {"type": "float", "required": True, "min": 0, "max": 5},
        "rating_count": {"type": "integer", "required": True, "min": 0},
        "features": {"type": "list", "required": True, "schema": {"type": "string"}},
    }
    validator = Validator(schema)
    assert validator.validate(hotel_data["info"]), validator.errors


def test_reviews():
    schema = {
        "id": {"type": "integer", "required": True},
        "date": {"type": "string", "required": True},  # You might want to check the date format
        "rating": {"type": "integer", "required": True, "min": 1, "max": 5},
        "title": {"type": "string", "required": True},
        "text": {"type": "string", "required": True},
        "votes": {"type": "integer", "required": True, "min": 0},
        "url": {"type": "string", "required": True},  # You can use regex to ensure valid URL
        "language": {"type": "string", "required": True},  # Consider enumerating the possible languages
        "platform": {"type": "string", "required": True},
        "author_id": {"type": "string", "required": True},
        "author_name": {"type": "string", "required": True},
        "author_username": {"type": "string", "required": True},
    }
    assert len(hotel_data["reviews"]) >= 20
    validator = Validator(schema)
    for review in hotel_data["reviews"]:
        assert validator.validate(review), validator.errors


def test_price():
    price_schema = {
        "date": {"type": "string", "regex": r"\d+-\d+-\d+", "required": True},
        "priceUSD": {"type": "integer", "min": 0, "required": True},
        "priceDisplay": {"type": "string", "regex": r"\$[\d,]+", "required": True},
    }
    validator = Validator(price_schema)
    for price in hotel_data["price"]:
        assert validator.validate(price), validator.errors
