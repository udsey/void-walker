import logging
from typing import List


from selenium.webdriver import Chrome, Remote
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains

from scr.setup import config

from scr.models import ConfigModel

logger = logging.getLogger(__name__)


def highlight_element(driver: Remote, element: WebElement, duration: int = 1000) -> None:
    driver.execute_script("""
        arguments[0].style.outline = '3px solid red';
        setTimeout(() => arguments[0].style.outline = '', arguments[1]);
    """, element, duration)


def configure_chrome() -> tuple[Chrome, WebDriverWait]:
    options = Options()
    options.add_experimental_option("prefs", {
    "profile.content_settings.exceptions.clipboard": {
        f"{config.root_url},*": {"last_modified": 1, "setting": 1}
    }})
    if not config.walkers_config.verbose:
        options.add_argument("--headless=new")
    driver = Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, config.wait_timeout)
    return driver, wait


def open_site(driver: Remote, 
              wait: WebDriverWait, 
              url: str) -> str:
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
    try:
        driver.quit()
        return config.status_config.close_browser.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.close_browser.on_fail
    

def press_explore(driver: Remote) -> str:
    try:
        explore_element = driver.find_element(by=By.CSS_SELECTOR, value="svg.lucide-shuffle")
        explore_element.click()
        return config.status_config.press_explore.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.press_explore.on_fail


def press_share(driver: Remote) -> str:
    try:
        share_element = driver.find_element(by=By.CSS_SELECTOR, value='svg.lucide-link')        
        share_element.click()
        url = driver.execute_script("return await navigator.clipboard.readText();")
        return url
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.press_share.on_fail


def clear_input(driver: Remote):
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
    try:
        input_element = driver.find_element(by=By.TAG_NAME, value="input")
        input_element.send_keys(text)
        return config.status_config.input_message.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.input_message.on_fail
    

def press_submit(driver: Remote):
    try:
        submit_element = driver.find_element(by=By.CSS_SELECTOR, value='svg.lucide-forward')        
        submit_element.click()
        return config.status_config.press_submit.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.press_submit.on_fail
        

def validate_cast_input(driver: Remote) -> str:
    try:
        input_element = driver.find_element(by=By.TAG_NAME, value="input")
        action_bar_element = input_element.find_element(by=By.XPATH, value='../../../..')
        warning_element = action_bar_element.find_elements(by=By.TAG_NAME, value='p')
        if warning_element:
            return warning_element[0].text
        else:
            return config.status_config.validate_cast_input.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.validate_cast_input.on_fail
    

def send_message(driver: Remote, text: str) -> str:
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
    try:
        word_cloud_element = driver.find_element(by=By.CLASS_NAME, value="cloud-group")
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
    try:
        nav_element = driver.find_element(by=By.TAG_NAME, value='nav')
        modal_elements = nav_element.find_elements(by=By.XPATH, value='./*')
        return [m.text for m in modal_elements]
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.check_available_modals.on_fail


def open_modal(driver: Remote, modal_name: str) -> str:
    try:
        modal_element = driver.find_element(By.XPATH, f"//*[text()='{modal_name}']")
        modal_element.click()
        return config.status_config.open_modal.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.open_modal.on_fail   
    

def close_modal(driver: Remote) -> str:
    try:
        modal_content_element = driver.find_element(by=By.CLASS_NAME, value="modal-content")
        modal_container_element = modal_content_element.find_element(by=By.XPATH, value='..')
        close_button_element = modal_container_element.find_element(By.XPATH, ".//button[text()='✕']")
        close_button_element.click()
        return config.status_config.close_modal.on_success
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.close_modal.on_fail   
        

def read_modal_content(driver: Remote) -> str:
    try:
        modal_content_element = driver.find_element(by=By.CLASS_NAME, value="modal-content")
        modal_content = modal_content_element.text
        return modal_content
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.read_modal_content.on_fail  


def interact_with_modal(driver: Remote, modal_name: str) -> str:
    try:
        response = open_modal(driver=driver, modal_name=modal_name)
        content = read_modal_content(driver=driver)
        response = close_modal(driver=driver)
        if content == config.status_config.read_modal_content.on_fail:
            return config.status_config.interact_with_modal.on_fail
        return content
    except Exception as e:
        logger.debug(e, exc_info=True)
        return config.status_config.interact_with_modal.on_fail 
    

def move_around(driver: Remote, dx: int, dy: int) -> str:
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
    return driver.current_url