import time
import re
import requests
import os
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === CONFIG ===
KNOWN_DATE = "June 1 to June 17"
REAL_URL = "http://localhost:8000/test_version2.html"  # ← Replace with real site
CHECK_INTERVAL = 10  # seconds

# === TELEGRAM CONFIG ===
BOT_TOKEN = "7864599472:AAEbBz9OZvIBJ2AinzBM3U2wtSzAXmwWIu0"
CHAT_ID = "177517058"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
last_checked_date = "Not yet checked"
last_update_id = 0  # will be set later

# === INIT: get last update_id to avoid reprocessing old messages
def get_latest_update_id():
    try:
        r = requests.get(f"{TELEGRAM_API}/getUpdates", timeout=5)
        updates = r.json()
        if updates.get("ok") and updates["result"]:
            return updates["result"][-1]["update_id"]
    except:
        pass
    return 0

last_update_id = get_latest_update_id()

# === SEND MESSAGE FUNCTION ===
def send_telegram_message(text):
    try:
        r = requests.post(f"{TELEGRAM_API}/sendMessage", data={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        })
        if r.status_code == 200:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Telegram sent: {text}")
        else:
            print("❌ Telegram failed:", r.text)
    except Exception as e:
        print("❌ Telegram send error:", e)

# === CHECK FOR COMMANDS FUNCTION ===
def check_for_commands():
    global last_update_id
    try:
        r = requests.get(f"{TELEGRAM_API}/getUpdates?offset={last_update_id + 1}", timeout=5)
        updates = r.json()

        if updates.get("ok"):
            for result in updates["result"]:
                last_update_id = result["update_id"]
                msg = result.get("message", {})
                text = msg.get("text", "").strip().lower()
                user_id = msg.get("chat", {}).get("id")

                if str(user_id) == CHAT_ID and text == "status":
                    send_telegram_message(f"📅 Last checked date: {last_checked_date}")

    except Exception as e:
        print("❌ Command check error:", e)

# === CHROME OPTIONS ===
options = uc.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

# You can add this if needed:
# options.add_argument("--disable-extensions")
# options.add_argument("--remote-debugging-port=9222")

# === MAIN MONITOR LOOP ===
while True:
    driver = uc.Chrome(options=options)
    driver.get(REAL_URL)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Stock')]"))
        )

        element = driver.find_element(By.XPATH, "//span[contains(text(), 'Stock')]")
        full_text = element.text.strip()

        if full_text.startswith("●"):
            full_text = full_text[1:].strip()

        match = re.search(r"[A-Za-z]+ \d{1,2} to [A-Za-z]+ \d{1,2}", full_text)
        date_range = match.group(0) if match else ""

        # Update the globally tracked value
        last_checked_date = date_range if date_range else "No valid date found"

        if not date_range:
            print(f"❌ No date range found — full text: {repr(full_text)}")
        elif date_range != KNOWN_DATE:
            print("✅ DATE RANGE CHANGE DETECTED")
            print(f"New range: {date_range}")
            send_telegram_message(f"🔔 <b>DATE CHANGE DETECTED</b>\nNew range: {date_range}")
        else:
            print("⏳ No change.")
            print(f"The current date range is: {date_range}")

    except Exception as e:
        print(f"❌ Error: {e}")

    finally:
        driver.quit()
        check_for_commands()
        time.sleep(CHECK_INTERVAL)
