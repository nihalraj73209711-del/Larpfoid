import requests
import time
import random
import string
import itertools
import logging
from datetime import datetime

# --- CONFIG ---
TELEGRAM_TOKEN = "8899506877:AAGl33w2JShzp6vL532iQSH7CTS1xnWXmRI"
CHAT_ID = "8395710783"
CHECK_INTERVAL = 45        # seconds between each check (stay under radar)
BATCH_PAUSE = 300          # seconds to pause after every 50 checks
SESSION_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# --- WORDLIST GENERATION ---
def generate_candidates():
    chars = string.ascii_lowercase + string.digits
    candidates = []

    # All 3-char mixed combos that contain at least one letter and one digit
    for combo in itertools.product(chars, repeat=3):
        s = "".join(combo)
        has_letter = any(c.isalpha() for c in s)
        has_digit = any(c.isdigit() for c in s)
        if has_letter and has_digit:
            candidates.append(s)

    # All 4-char mixed combos that contain at least one letter and one digit
    for combo in itertools.product(chars, repeat=4):
        s = "".join(combo)
        has_letter = any(c.isalpha() for c in s)
        has_digit = any(c.isdigit() for c in s)
        if has_letter and has_digit:
            candidates.append(s)

    random.shuffle(candidates)
    return candidates

# --- TELEGRAM ---
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        if r.status_code != 200:
            log.error(f"Telegram error: {r.text}")
    except Exception as e:
        log.error(f"Telegram send failed: {e}")

# --- INSTAGRAM CHECK ---
def check_username(session, username):
    url = f"https://www.instagram.com/{username}/"
    try:
        r = session.get(url, timeout=10, allow_redirects=True)
        if r.status_code == 404:
            return "available"
        elif r.status_code == 200:
            # Check if it's a real profile or a soft 404
            if '"@context"' in r.text or 'og:title' in r.text:
                return "taken"
            else:
                return "available"
        elif r.status_code == 429:
            return "rate_limited"
        else:
            return f"unknown_{r.status_code}"
    except requests.exceptions.Timeout:
        return "timeout"
    except Exception as e:
        return f"error"

# --- MAIN LOOP ---
def main():
    log.info("IGWatch starting up...")
    send_telegram("🟢 <b>IGWatch is live</b>\nScanning 3-4 letter mixed usernames. You'll be pinged the moment one is available.")

    session = requests.Session()
    session.headers.update(SESSION_HEADERS)

    candidates = generate_candidates()
    log.info(f"Generated {len(candidates)} candidates to check")

    checked = 0
    available_found = []

    for username in candidates:
        result = check_username(session, username)
        checked += 1

        if result == "available":
            msg = (
                f"🔥 <b>@{username} is AVAILABLE</b>\n"
                f"👉 instagram.com/{username}\n"
                f"Grab it NOW before it's gone."
            )
            log.info(f"AVAILABLE: @{username}")
            send_telegram(msg)
            available_found.append(username)

        elif result == "rate_limited":
            log.warning(f"Rate limited — pausing 10 minutes")
            send_telegram(f"⚠️ Rate limited by Instagram. Pausing 10 minutes then resuming.")
            time.sleep(600)
            session = requests.Session()
            session.headers.update(SESSION_HEADERS)

        else:
            log.info(f"@{username} → {result}")

        # Pause every 50 checks
        if checked % 50 == 0:
            log.info(f"Checked {checked}/{len(candidates)} — pausing {BATCH_PAUSE}s")
            send_telegram(f"📊 Progress: {checked}/{len(candidates)} checked | Found: {len(available_found)} available")
            time.sleep(BATCH_PAUSE)
        else:
            # Random delay between checks to look human
            delay = CHECK_INTERVAL + random.uniform(-10, 15)
            time.sleep(max(delay, 20))

    send_telegram(f"✅ Scan complete. Checked {checked} usernames. Found {len(available_found)} available:\n" + "\n".join(f"@{u}" for u in available_found))
    log.info("Scan complete.")

if __name__ == "__main__":
    main()
