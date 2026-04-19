"""
IVT Tracker Pipeline — full daily run: scrape → classify → notify.
"""

import os

from dotenv import load_dotenv

load_dotenv(override=True)

from pathlib import Path
from botasaurus.browser import Browser, Driver, BrowserConfig

from .db import init_db, get_unclassified_posts, update_classification
from .classifier import SYSTEM_PROMPT as LLM_SYSTEM, classify_batch
from .notifier import send_call_notification

BROWSER_PROFILE = "ivt_tracker_main"

USERNAME = os.getenv("IVT_USERNAME")
PASSWORD = os.getenv("IVT_PASSWORD")


def run_scrape():
    """Launch Botasaurus, login & scrape posts → posts.json"""

    def scrape_posts(driver: Driver, _):
        url = "https://app.interactivtrading.com/"
        driver.get(url)

        # Login if needed
        if driver.is_element_present('input[type="text"]', wait=5):
            driver.type('input[type="text"]', USERNAME)
            driver.type('input[type="password"]', PASSWORD)
            btn = driver.select('button[type="submit"]') or driver.select('button.kXHAcR')
            if btn:
                btn.click()
            for _ in range(20):
                if not driver.is_element_present('input[type="text"]', wait=0.5):
                    break
                import time; time.sleep(1)

        # Wait for posts to load
        import time; time.sleep(5)

        posts = []
        for post in driver.select_all('.sc-embLYd'):
            try:
                cat = post.select('h3').text if post.select('h3') else "Unknown"
                content = post.select('.sc-fMfAsl').text if post.select('.sc-fMfAsl') else ""
                author_block = post.select('.sc-kXXgDA')
                if author_block:
                    date_el = author_block.select('p')
                    date = date_el.text if date_el else ""
                    author = author_block.text.replace(date, "").strip()
                else:
                    author = "Unknown"
                    date = "Unknown"

                posts.append({
                    "author": author,
                    "date": date,
                    "category": cat,
                    "content": content,
                })
            except Exception as e:
                print(f"Error extracting post: {e}")

        import json
        output = Path(__file__).parent.parent / "posts.json"
        with open(output, "w", encoding="utf-8") as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
        print(f"Scraped {len(posts)} posts")


    Browser(BrowserConfig(headless=True, profile=BROWSER_PROFILE, block_images=True)).run(scrape_posts)


def run_pipeline():
    """Full pipeline: scrape → store → classify → notify."""
    init_db()

    # 1. Scrape
    print("[pipeline] scraping...")
    run_scrape()

    # 2. ingest
    from .classifier import ingest_posts
    new_count = ingest_posts()
    print(f"[pipeline] {new_count} new posts stored")

    # 3. classify unclassified
    unclassified = get_unclassified_posts()
    if not unclassified:
        print("[pipeline] nothing to classify")
        return

    print(f"[pipeline] classifying {len(unclassified)} posts with qwen3.6-plus")
    results = classify_batch(unclassified)

    # 4. save + notify
    notified = 0
    for r in results:
        pid, cls = r["post_id"], r["classification"]
        update_classification(pid, cls)
        if cls.get("type") in ("new_call", "follow_up", "close"):
            post = next((p for p in unclassified if p["id"] == pid), None)
            if post:
                send_call_notification(post, cls)
                notified += 1

    print(f"[pipeline] done. {notified} call notifications sent.")


if __name__ == "__main__":
    run_pipeline()
