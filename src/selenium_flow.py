import os
import yaml
import time
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.utils.human import human_type, human_pause, human_mouse_wiggle
from src.utils.session import save_cookies, load_cookies

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

def _wait_and_get(driver, selector, timeout=15):
    """Try CSS or simple text selector. Accept comma-separated alternatives."""
    parts = [s.strip() for s in selector.split(",")]
    end = time.time() + timeout
    last_exc = None
    while time.time() < end:
        for s in parts:
            try:
                if s.startswith("button:has-text("):
                    # crude text button match
                    text = s.split("button:has-text(")[1].rstrip(")").strip().strip('"').strip("'")
                    elems = driver.find_elements(By.TAG_NAME, "button")
                    for e in elems:
                        if e.is_displayed() and text.lower() in e.text.lower():
                            return e
                else:
                    elem = driver.find_element(By.CSS_SELECTOR, s)
                    if elem.is_displayed():
                        return elem
            except Exception as ex:
                last_exc = ex
        time.sleep(0.2)
    if last_exc:
        raise last_exc
    raise NoSuchElementException(f"Not found: {selector}")

def start_driver(headless=False, user_data_dir=None):
    """Start undetected Chrome. user_data_dir helps keep sessions like a real profile."""
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=en-US,en")
    if user_data_dir:
        options.add_argument(f"--user-data-dir={user_data_dir}")
    driver = uc.Chrome(options=options)
    driver.set_window_size(1280, 900)
    return driver

def login_if_needed(driver, cfg):
    """Use cookies if present; otherwise perform a human-like login once."""
    # Try cookies first
    if load_cookies(driver, base_url=cfg["login"]["url"]):
        driver.get(cfg["login"]["url"])
        # If already authenticated, Dropbox will redirect to home quickly.
        time.sleep(3)
        if "login" not in driver.current_url.lower():
            print("✅ Session restored; already logged in.")
            return True

    # No cookie success; do manual login
    print("🌐 Starting Dropbox login flow…")
    driver.get(cfg["login"]["url"])
    human_mouse_wiggle(driver)

    # cookie banner
    try:
        btn = _wait_and_get(driver, cfg["login"]["cookie_accept"], timeout=5)
        btn.click()
        human_pause()
    except Exception:
        pass

    # email
    email_input = _wait_and_get(driver, cfg["login"]["email_selector"], timeout=20)
    email_input.click()
    human_type(email_input, EMAIL)
    human_pause()
    # Continue
    cont = _wait_and_get(driver, cfg["login"]["continue_button"], timeout=20)
    cont.click()
    time.sleep(2)

    # Password may be on same page or new route
    try:
        pwd_input = _wait_and_get(driver, cfg["login"]["password_selector"], timeout=25)
        pwd_input.click()
        human_type(pwd_input, PASSWORD)
        human_pause()
    except Exception:
        print("⚠️ Password field not immediately visible; if CAPTCHA appears, solve it once.")
        # Give user time to solve CAPTCHA / 2FA if shown
        for _ in range(40):
            if "login" not in driver.current_url.lower():
                break
            time.sleep(1)

    # Submit
    try:
        submit = _wait_and_get(driver, cfg["login"]["submit_selector"], timeout=10)
        submit.click()
    except Exception:
        # try ENTER on password field
        try:
            pwd_input.send_keys(Keys.ENTER)
        except Exception:
            pass

    # --- 🧩 New section: Handle "Set up later" or "Skip" 2FA setup ---
    try:
        print("🔍 Checking for 'Set up later' or 'Skip' button...")
        for _ in range(15):  # 15 seconds scan loop
            buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Set up later') or contains(., 'Skip') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'set up later')]")
            if buttons:
                human_mouse_wiggle(driver)
                buttons[0].click()
                print("⏩ Clicked 'Set up later' to skip 2FA setup.")
                time.sleep(4)
                break
            time.sleep(1)
    except Exception as e:
        print(f"⚠️ Could not handle 2FA setup screen: {e}")

    # Wait & save cookies
    time.sleep(6)
    if "login" in driver.current_url.lower():
        print("⚠️ Still on login page. If you see CAPTCHA, solve it, then press Enter in your terminal to continue.")
        try:
            input("⏸️  Press Enter after solving CAPTCHA / finishing login…")
        except EOFError:
            pass
        time.sleep(3)

    if "login" in driver.current_url.lower():
        print("❌ Login did not complete. Check the window and try again.")
        return False

    print("✅ Logged in.")
    save_cookies(driver)
    return True

def goto_members_page(driver, cfg):
    print("👥 Navigating to Members page…")
    driver.get(cfg["members"]["page"])
    time.sleep(3)

def invite_user(driver, cfg, email):
    print(f"📨 Inviting: {email}")
    goto_members_page(driver, cfg)

    # Find an Invite button
    for sel in cfg["selectors"]["invite_button"]:
        try:
            btn = _wait_and_get(driver, sel, timeout=8)
            btn.click()
            break
        except Exception:
            continue
    else:
        driver.save_screenshot("invite_debug.png")
        print("❌ Could not find Invite button. Saved invite_debug.png")
        return False

    time.sleep(1)
    # email input
    for sel in cfg["selectors"]["invite_email_input"]:
        try:
            inbox = _wait_and_get(driver, sel, timeout=8)
            inbox.click()
            human_type(inbox, email)
            break
        except Exception:
            continue
    else:
        driver.save_screenshot("invite_email_debug.png")
        print("❌ Could not find invite email input. Saved invite_email_debug.png")
        return False

    # send invite
    for sel in cfg["selectors"]["invite_send_button"]:
        try:
            send = _wait_and_get(driver, sel, timeout=8)
            send.click()
            time.sleep(2)
            print("✅ Invite submitted.")
            return True
        except Exception:
            continue

    driver.save_screenshot("invite_send_debug.png")
    print("❌ Could not find Send Invite button. Saved invite_send_debug.png")
    return False

def remove_user(driver, cfg, email):
    print(f"🗑️ Removing user: {email}")
    goto_members_page(driver, cfg)
    time.sleep(3)

    try:
        # Step 1: Find the table row containing the target email
        rows = driver.find_elements(By.XPATH, "//tr")
        target_row = None
        for r in rows:
            if email.lower() in r.text.lower():
                target_row = r
                break

        if not target_row:
            raise NoSuchElementException(f"User {email} not found in Members table.")

        # Step 2: Click the checkbox
        checkbox = target_row.find_element(By.XPATH, ".//input[@type='checkbox']")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
        time.sleep(0.5)
        checkbox.click()
        print("✅ Selected user checkbox.")
        time.sleep(1)

        # Step 3: Try 'Suspend' or 'Remove'
        try:
            suspend_btn = driver.find_element(By.XPATH, "//button[contains(., 'Suspend')]")
            driver.execute_script("arguments[0].click();", suspend_btn)
            print("⚠️ Clicked Suspend button.")
        except Exception:
            print("🧭 Trying 'More' menu for remove option.")
            more_btns = driver.find_elements(By.XPATH, "//button[contains(., 'More')]")
            if more_btns:
                driver.execute_script("arguments[0].click();", more_btns[0])
                time.sleep(1)
                try:
                    remove_opt = driver.find_element(By.XPATH, "//span[contains(., 'Remove') or contains(., 'Suspend')]")
                    driver.execute_script("arguments[0].click();", remove_opt)
                    print("✅ Clicked Remove/Suspend option.")
                except Exception:
                    print("❌ Could not find Remove/Suspend option in dropdown.")
            else:
                print("❌ No 'More' button found.")

        # Step 4: Wait for confirmation modal and click the final confirm button
        time.sleep(2)
        try:
            confirm_btn = _wait_and_get(driver, "button:has-text('Suspend members'), button:has-text('Remove members')", timeout=8)
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", confirm_btn)
            time.sleep(0.5)
            confirm_btn.click()
            print("✅ Confirmed suspension/removal in popup.")
        except Exception as e:
            print(f"⚠️ Could not find confirm button: {e}")

        time.sleep(3)
        print(f"✅ Removal process completed for {email}.")
        return True

    except Exception as e:
        print(f"❌ Could not remove user '{email}': {e}")
        driver.save_screenshot("remove_member_debug.png")
        return False


def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)
def open_team_and_manage(driver, cfg, team_name):
    """Open the specified Dropbox team folder and list/invite/remove members."""
    print(f"📂 Opening team folder: {team_name}")
    time.sleep(3)

    try:
        # find the team folder by text (works for the list and suggestion area)
        team_elem = None
        possible_selectors = [
            f"//span[contains(text(), '{team_name}')]",        # main list
            f"//div[contains(text(), '{team_name}')]",         # suggestion card
            f"//a[contains(., '{team_name}')]"                 # links
        ]

        for sel in possible_selectors:
            elems = driver.find_elements(By.XPATH, sel)
            if elems:
                team_elem = elems[0]
                break

        if not team_elem:
            raise NoSuchElementException(f"Team '{team_name}' not found.")

        # Scroll and click using JS to bypass overlays
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", team_elem)
        time.sleep(1)
        try:
            team_elem.click()
        except Exception:
            print("⚠️ Regular click failed, trying JS click.")
            driver.execute_script("arguments[0].click();", team_elem)

        time.sleep(5)

        # Sometimes Dropbox opens in a new tab — handle that
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            print("🪟 Switched to new tab.")

        print(f"✅ Opened '{team_name}' successfully.")

    except Exception as e:
        print(f"❌ Could not open team '{team_name}': {e}")
        driver.save_screenshot("team_open_debug.png")
        return

    # After opening, go to Members management page
    goto_members_page(driver, cfg)
    print("👥 Now on Members dashboard.")

    # Member list
    try:
        rows = driver.find_elements(By.XPATH, "//tr")
        print(f"📋 Found {len(rows)} member entries (approx).")
        for r in rows[:10]:
            print(" -", r.text)
    except Exception:
        print("⚠️ Could not list members (table not visible).")

    # Interactive terminal menu
    while True:
        print("\n🧭 Choose an action:")
        print("  1️⃣  List members")
        print("  2️⃣  Invite member")
        print("  3️⃣  Remove member")
        print("  4️⃣  Exit")
        choice = input("👉 Enter choice: ").strip()

        if choice == "1":
            rows = driver.find_elements(By.XPATH, "//tr")
            print(f"\n👥 Listing members ({len(rows)} rows):")
            for r in rows:
                print(" -", r.text)

        elif choice == "2":
            email = input("📨 Enter email to invite: ").strip()
            invite_user(driver, cfg, email)

        elif choice == "3":
            email = input("🗑️ Enter email to remove: ").strip()
            remove_user(driver, cfg, email)

        elif choice == "4":
            print("🚪 Exiting team management view.")
            break

        else:
            print("❌ Invalid choice. Try again.")
