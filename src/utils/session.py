import os
import json

SESSION_FILE = "session_cookies.json"

def save_cookies(driver, domain_filter=".dropbox.com"):
    cookies = driver.get_cookies()
    if domain_filter:
        cookies = [c for c in cookies if domain_filter in c.get("domain","")]
    with open(SESSION_FILE, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"💾 Saved session cookies -> {SESSION_FILE}")

def load_cookies(driver, base_url="https://www.dropbox.com"):
    if not os.path.exists(SESSION_FILE):
        return False
    try:
        driver.get(base_url)
        with open(SESSION_FILE, "r") as f:
            cookies = json.load(f)
        for c in cookies:
            # Selenium expects expiry to be int if present
            if "expiry" in c and isinstance(c["expiry"], float):
                c["expiry"] = int(c["expiry"])
            driver.add_cookie(c)
        driver.get(base_url)  # refresh with cookies applied
        print("🔁 Loaded session cookies.")
        return True
    except Exception as e:
        print("⚠️ Could not load cookies:", e)
        return False
