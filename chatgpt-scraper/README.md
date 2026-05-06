# ChatGPT.com Scraper

This scraper uses [scrapfly.io](https://scrapfly.io/) and Python to scrape data from chatgpt.com.

## What it scrapes
- Shared conversation pages: url, title, model, created_at, messages
- GPTs search/discovery pages: name, url, description, author, category

## Fair Use Disclaimer

This code is provided for educational purposes only. Review chatgpt.com's Terms of Service before scraping.

## Setup and Use

0. Requires Python 3.10+ and [Poetry](https://python-poetry.org/docs/#installation).
1. Get a Scrapfly API key from https://scrapfly.io/dashboard and export it:
   ```shell
   export SCRAPFLY_KEY="YOUR KEY"
   ```
2. Install:
   ```shell
   cd chatgpt-scraper
   poetry install --no-root
   ```
3. Run example:
   ```shell
   poetry run python run.py
   ```
4. Run tests:
   ```shell
   poetry install
   poetry run pytest test.py
   ```
