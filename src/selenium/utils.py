"""Selenium utils."""


from selenium.webdriver import Remote
from selenium.webdriver.remote.webelement import WebElement


def highlight_element(driver: Remote,
                      element: WebElement,
                      duration: int = 1000) -> None:
    """Highlight given element."""
    driver.execute_script("""
        arguments[0].style.outline = '3px solid red';
        setTimeout(() => arguments[0].style.outline = '', arguments[1]);
    """, element, duration)
