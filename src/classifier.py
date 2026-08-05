"""
LLM classifier — reads posts.json, classifies each, stores results in SQLite.
"""

import os
import json
from pathlib import Path

from openai import OpenAI

from .db import store_post, update_classification, get_unclassified_posts

MODEL = os.getenv("CLASSIFIER_MODEL", "qwen/qwen3.6-plus")


def ingest_posts(posts_path: Path | None = None):
    """Read posts.json and store new ones in the DB."""
    if posts_path is None:
        posts_path = Path(__file__).parent.parent / "posts.json"
    if not posts_path.exists():
        return 0

    with open(posts_path, "r", encoding="utf-8") as f:
        posts = json.load(f)

    count = 0
    for p in posts:
        # Include images in hash for uniqueness
        images_str = json.dumps(p.get("images", []), sort_keys=True)
        content_with_images = f"{p.get('content', '')}|||{images_str}"
        
        is_new, _ = store_post(
            p.get("author", ""),
            p.get("date", ""),
            p.get("category", ""),
            content_with_images,
        )
        if is_new:
            count += 1
    return count


SYSTEM_PROMPT = """You are a financial message classifier for a trading community feed.
For each message, determine:

**type** (exactly one):
- "new_call" — A NEW trading signal (buy/sell) with entry details
- "follow_up" — Update on an existing call (add TP, move SL, partial close)
- "close" — Closing a position, take profit hit, stop loss hit, exit
- "general" — Market analysis, news, casual talk, anything else

**asset** — The ticker/symbol (XAUUSD, EURUSD, BTCUSD, NQ, ES, etc.)
**direction** — "buy", "sell", or null
**entry_zone** — Price zone if mentioned, null otherwise
**stop_loss** — SL level if mentioned, null otherwise
**take_profit** — TP levels if mentioned, null otherwise
**confidence** — 0.0 to 1.0, how confident you are in the classification
**rationale** — Short explanation of your classification

Respond with a JSON object containing a "classifications" array, one object per post, in order.
Return ONLY valid JSON, no markdown, no explanation."""


def classify_batch(posts: list[dict]) -> list[dict]:
    """Send unclassified posts to LLM in one batch."""
    if not posts:
        return []

    messages_text = ""
    for p in posts:
        messages_text += f"\n--- POST_ID: {p['id']} ---\n"
        if p.get("author"):
            messages_text += f"[author: {p['author']}]\n"
        if p.get("category"):
            messages_text += f"[category: {p['category']}]\n"
        messages_text += f"{p['content']}\n"

    client = OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": messages_text},
        ],
        temperature=0.1,
        max_tokens=2000,
    )

    raw = resp.choices[0].message.content.strip()

    # Strip potential markdown code fences
    if raw.startswith("```"):
        raw = raw.split("```", 2)[-2] if raw.count("```") >= 2 else raw[3:]
    raw = raw.strip()

    parsed = json.loads(raw)

    classifications = parsed.get("classifications", parsed)
    if not isinstance(classifications, list):
        return []

    results = []
    for i, item in enumerate(classifications):
        if i < len(posts):
            results.append({
                "post_id": posts[i]["id"],
                "classification": item,
            })
    return results
