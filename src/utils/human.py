import time
import random
from selenium.webdriver.common.action_chains import ActionChains

def human_pause(min_ms=80, max_ms=200):
    time.sleep(random.uniform(min_ms/1000.0, max_ms/1000.0))

def human_type(elem, text):
    for ch in text:
        elem.send_keys(ch)
        human_pause(30, 120)

def human_mouse_wiggle(driver):
    try:
        actions = ActionChains(driver)
        for _ in range(3):
            actions.move_by_offset(random.randint(3, 15), random.randint(3, 15)).perform()
            human_pause(60, 150)
    except Exception:
        pass
