"""Selenium functions."""

import logging
from typing import List

from selenium.webdriver import ActionChains, Chrome, Remote
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from src.setup import config

logger = logging.getLogger(__name__)



def configure_chrome() -> tuple[Chrome, WebDriverWait]:
    """Configure browser."""
    options = Options()
    options.add_experimental_option("prefs", {
    "profile.content_settings.exceptions.clipboard": {
        f"{config.root_url},*": {"last_modified": 1, "setting": 1}
    }})
    if not config.walkers_config.verbose:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = "/usr/bin/chromium"

    try:
        driver = Chrome(service=Service(ChromeDriverManager().install()),
                        options=options)
    except Exception:
        driver = Chrome(service=Service("/usr/bin/chromedriver"),
                         options=options)
    wait = WebDriverWait(driver, config.wait_timeout)
    return driver, wait


def open_site(driver: Remote,
              wait: WebDriverWait,
              url: str) -> str:
    """Open website."""
    try:
        driver.get(url)
        wait.until(
            method=EC.presence_of_element_located(
                locator=(By.TAG_NAME, "input")))
        return config.status_config.open_site.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.open_site.on_fail


def close_browser(driver: Remote) -> str:
    """Close browser"""
    try:
        driver.quit()
        return config.status_config.close_browser.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.close_browser.on_fail


def press_explore(driver: Remote) -> str:
    """Press explore button"""
    try:
        explore_element = driver.find_element(by=By.CSS_SELECTOR,
                                              value="svg.lucide-shuffle")
        explore_element.click()
        return config.status_config.press_explore.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.press_explore.on_fail


def press_share(driver: Remote) -> str:
    """Press share button. On success returns url."""
    try:
        share_element = driver.find_element(by=By.CSS_SELECTOR,
                                            value='svg.lucide-link')
        share_element.click()
        url = driver.execute_script(
            "return await navigator.clipboard.readText();")
        return url
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.press_share.on_fail


def clear_input(driver: Remote):
    """Clear input."""
    try:
        input_element = driver.find_element(by=By.TAG_NAME, value="input")
        input_element.clear()
        text = input_element.get_attribute("value")
        if text:
            return config.status_config.clear_input.on_fail
        return config.status_config.clear_input.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.clear_input.on_fail


def input_message(driver: Remote, text: str) -> str:
    """Insert message."""
    try:
        input_element = driver.find_element(by=By.TAG_NAME, value="input")
        input_element.send_keys(text)
        return config.status_config.input_message.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.input_message.on_fail


def press_submit(driver: Remote):
    """Press submit button."""
    try:
        submit_element = driver.find_element(by=By.CSS_SELECTOR,
                                             value='svg.lucide-forward')
        submit_element.click()
        return config.status_config.press_submit.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.press_submit.on_fail


def validate_cast_input(driver: Remote) -> str:
    """Check input errors."""
    try:
        input_element = driver.find_element(by=By.TAG_NAME, value="input")
        action_bar_element = input_element.find_element(
            by=By.XPATH, value='../../../..')
        warning_element = action_bar_element.find_elements(
            by=By.TAG_NAME, value='p')
        if warning_element:
            return warning_element[0].text
        else:
            return config.status_config.validate_cast_input.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.validate_cast_input.on_fail


def send_message(driver: Remote, text: str) -> str:
    """Send message."""
    try:
        response = clear_input(driver=driver)
        response = input_message(driver=driver, text=text)
        response = press_submit(driver=driver)
        response = validate_cast_input(driver=driver)
        if response == config.status_config.validate_cast_input.on_success:
            return config.status_config.send_message.on_success
        return f"{config.status_config.send_message.on_fail}: {response}"
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.send_message.on_fail


def read_visible_messages(driver: Remote) -> List[str]:
    """Return all visible messages."""
    try:
        messages = driver.execute_script("""
            const cloud = document.querySelector('.cloud-group');
            const viewportWidth = window.innerWidth;
            const viewportHeight = window.innerHeight;
            const seen = new Map();
            Array.from(cloud.querySelectorAll('tspan'))
                .filter(el => {
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 &&
                        rect.top >= 0 &&
                        rect.left >= 0 &&
                        rect.bottom <= viewportHeight &&
                        rect.right <= viewportWidth &&
                        el.textContent.trim() !== '';
                })
                .forEach(el => {
                    const parent = el.closest('text');
                    if (!seen.has(parent)) seen.set(parent, []);
                    seen.get(parent).push(el.textContent);
                });
            return Array.from(seen.values()).map(lines => lines.join(' '));
        """)
        return messages
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.read_visible_messages.on_fail


def check_available_modals(driver: Remote) -> str:
    """Return list of modals."""
    try:
        nav_element = driver.find_element(by=By.TAG_NAME, value='nav')
        modal_elements = nav_element.find_elements(by=By.XPATH, value='./*')
        return [m.text for m in modal_elements]
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.check_available_modals.on_fail


def open_modal(driver: Remote, modal_name: str) -> str:
    """Open modal."""
    try:
        modal_element = driver.find_element(By.XPATH,
                                            f"//*[text()='{modal_name}']")
        modal_element.click()
        return config.status_config.open_modal.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.open_modal.on_fail


def close_modal(driver: Remote) -> str:
    """Close modal."""
    try:
        modal_content_element = driver.find_element(by=By.CLASS_NAME,
                                                    value="modal-content")
        modal_container_element = modal_content_element.find_element(
            by=By.XPATH, value='..')
        close_button_element = modal_container_element.find_element(
            By.XPATH, ".//button[text()='✕']")
        close_button_element.click()
        return config.status_config.close_modal.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.close_modal.on_fail


def read_modal_content(driver: Remote) -> str:
    """Return modal content."""
    try:
        modal_content_element = driver.find_element(by=By.CLASS_NAME,
                                                    value="modal-content")
        modal_content = modal_content_element.text
        return modal_content
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.read_modal_content.on_fail


def interact_with_modal(driver: Remote, modal_name: str) -> str:
    """Opens modal, extract content and close."""
    try:
        open_modal(driver=driver, modal_name=modal_name)
        content = read_modal_content(driver=driver)
        close_modal(driver=driver)
        if content == config.status_config.read_modal_content.on_fail:
            return config.status_config.interact_with_modal.on_fail
        return content
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.interact_with_modal.on_fail


def move_around(driver: Remote, dx: int, dy: int) -> str:
    """Simulate mouse move canvas behaviour."""
    try:
        canvas_element = driver.find_element(By.TAG_NAME, "svg")
        width = driver.execute_script("return window.innerWidth")
        height = driver.execute_script("return window.innerHeight")

        dx = max(-(width // 2), min(dx, width // 2))
        dy = max(-(height // 2), min(dy, height // 2))
        ActionChains(driver)\
            .move_to_element(canvas_element)\
            .click_and_hold()\
            .move_by_offset(dx, dy)\
            .release()\
            .perform()
        return config.status_config.move_around.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.move_around.on_fail


def get_current_url(driver) -> str:
    """Return current url."""
    return driver.current_url
