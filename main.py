#!/usr/bin/env python3
import argparse
import os
from src.selenium_flow import (
    start_driver, load_config, login_if_needed,
    goto_members_page, invite_user, remove_user, open_team_and_manage 
)

def parse_args():
    p = argparse.ArgumentParser(description="Dropbox Provisioning via Selenium (visible, session-persistent).")
    p.add_argument("--visible", action="store_true", help="Show browser window (recommended for first run).")
    p.add_argument("--login", action="store_true", help="Force login flow (ignores existing cookies).")
    p.add_argument("--list", action="store_true", help="Just navigate to Members page and pause (visual list).")
    p.add_argument("--invite", type=str, help="Email to invite.")
    p.add_argument("--remove", type=str, help="Email to remove.")
    p.add_argument("--profile", type=str, default=None, help="Optional Chrome user-data-dir to persist full profile.")
    p.add_argument("--team", type=str, help="Open specific team and manage members.")
    return p.parse_args()

def main():
    args = parse_args()
    cfg = load_config("config.yaml")
    driver = start_driver(headless=not args.visible, user_data_dir=args.profile)

    try:
        if args.login:
            # Force a fresh login (don’t load cookies)
            pass
        # Ensure we’re authenticated (load or perform login if needed)
        ok = login_if_needed(driver, cfg)
        if not ok:
            print("❌ Login failed. Exiting.")
            return
        if args.team:
            open_team_and_manage(driver, cfg, args.team)
            return

        if args.list:
            goto_members_page(driver, cfg)
            if args.visible:
                input("👀 Inspect members page, then press Enter to quit…")
            return

        if args.invite:
            invite_user(driver, cfg, args.invite)
            if args.visible:
                input("✅ Invite done (check UI). Press Enter to close…")
            return

        if args.remove:
            remove_user(driver, cfg, args.remove)
            if args.visible:
                input("✅ Removal attempted (check UI). Press Enter to close…")
            return

        # Default: just open members page
        goto_members_page(driver, cfg)
        if args.visible:
            input("✨ Ready. Press Enter to close.")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
