"""
Telegram notification sender for trading calls.
"""

import os
import requests


def send_call_notification(post: dict, classification: dict):
    """Format and send a call notification to Telegram."""
    ctype = classification.get("type", "").upper()
    asset = classification.get("asset", "?")
    direction = classification.get("direction", "")
    entry = classification.get("entry_zone")
    sl = classification.get("stop_loss")
    tp = classification.get("take_profit")
    rationale = classification.get("rationale", "")
    confidence = classification.get("confidence", 0)

    # Emoji per type
    emoji_map = {
        "new_call": "📢",
        "follow_up": "🔄",
        "close": "✅",
    }
    emoji = emoji_map.get(classification.get("type", ""), "📢")

    # Direction emoji
    dir_emoji = ""
    if direction == "buy":
        dir_emoji = "🟢 BUY"
    elif direction == "sell":
        dir_emoji = "🔴 SELL"

    parts = []
    # Header
    parts.append(f"{emoji} {ctype}")
    if dir_emoji:
        parts.append(f"{dir_emoji} {asset}")
    else:
        parts.append(f"{asset}")

    # Details
    details = []
    if entry and entry not in ("", "null", "None"):
        details.append(f"Entry: {entry}")
    if sl and sl not in ("", "null", "None"):
        details.append(f"SL: {sl}")
    if tp and tp not in ("", "null", "None"):
        details.append(f"TP: {tp}")

    if details:
        parts.append(" | ".join(details))

    if rationale:
        parts.append("")  # blank line
        parts.append(f"📝 {rationale}")

    parts.append(f"Confidence: {confidence:.0%}")

    message = "\n".join(parts)

    _send_telegram_message(message)


def _send_telegram_message(text: str):
    """Send a message to the configured Telegram chat via the bot API."""
    bot_token = os.getenv("IVT_TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("IVT_TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("[notifier] Skipping: no Telegram tokens configured")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print("[notifier] Notification sent successfully")
        else:
            print(f"[notifier] Failed to send: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[notifier] Error sending notification: {e}")
