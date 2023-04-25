"""Selenium web scraping module."""
from __future__ import annotations

import logging
from pathlib import Path
from sys import platform

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

import autogpt.processing.text as summary
from autogpt.config import Config
from autogpt.processing.html import extract_hyperlinks, format_hyperlinks

FILE_DIR = Path(__file__).parent.parent
CFG = Config()

def browse_website(url: str, question: str) -> tuple[str, WebDriver]:
    """Browse a website and return the answer and links to the user

    Args:
        url (str): The url of the website to browse
        question (str): The question asked by the user

    Returns:
        Tuple[str, WebDriver]: The answer and links to the user and the webdriver
    """
    driver = create_driver()
    driver, text = scrape_text_with_selenium(url, driver)
    add_header(driver)
    summary_text = summary.summarize_text(url, text, question, driver)
    links = scrape_links_with_selenium(driver, url)

    # Limit links to 5
    if len(links) > 5:
        links = links[:5]
    close_browser(driver)
    return f"Answer gathered from website: {summary_text} \n \n Links: {links}", driver

def open_website_in_browser(url: str, question: str) -> tuple[str, WebDriver]:
    driver = create_driver()

    driver.get(url)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    return f"Website is now open using the selenium webdriver", driver

def identify_form_field(driver):
    body_text = driver.find_element(By.XPATH, "/html/body").text

    return f"Current valid html", body_text

def enter_text_into_form_field(driver, field_name, text):
    body_text = driver.find_element(By.XPATH, "/html/body").text
    field = driver.find_element(field_name)
    field.sendkeys(text)

    return f"Current valid html", body_text

def navigate_by_click_button(driver, button_text):
    try:
        buttons = driver.find_element(button_text).click()


        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        return f"Current valid website context", get_updated_html_context(driver)
    except:
        return "Error: That button doesn't exist, please identify the correct button first"

def get_updated_html_context(driver):
    buttons = driver.find_elements(By.XPATH,'//button')
    button_text = list(map(lambda button: button.text, buttons))

    inputs = driver.find_elements(By.XPATH,"//input[@type='text' or @type='password']")
    input_text = list(map(lambda input: input.text, inputs))

    body = driver.find_elements(By.XPATH, "/html/body")
    body_text = list(map(lambda body: body.text, body))
    return {"body_text": body_text, "buttons": button_text, "inputs": input_text}

def get_updated_html(driver):
    try:
        return f"Current valid website context", get_updated_html_context(driver)
    except:
        return "Error: Can't seem to get html, please stop doing QA and get some help"

def find_button_name(driver):
    try:
        return f"Current valid website context", get_updated_html_context(driver)
    except:
        return "Error: That button doesn't exist, please identify the correct button first"

def click_button(driver):
    try:
        buttons = driver.find_elements(By.XPATH,'//button').text
        inputs = driver.find_elements(By.XPATH,"//input[@type='text' or @type='password']").text
        body_text = driver.find_elements(By.XPATH, "/html/body").text

        return f"Current valid website context", {"body_text": body_text, "buttons": buttons, "inputs": inputs}
    except:
        return "Error: That button doesn't exist, please identify the correct button first"

def create_driver():
    options_available = {
        "chrome": ChromeOptions,
        "safari": SafariOptions,
        "firefox": FirefoxOptions,
    }

    options = options_available[CFG.selenium_web_browser]()
    options.add_experimental_option("detach", True)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.49 Safari/537.36"
    )

    if CFG.selenium_web_browser == "firefox":
        driver = webdriver.Firefox(
            executable_path=GeckoDriverManager().install(), options=options
        )
    elif CFG.selenium_web_browser == "safari":
        # Requires a bit more setup on the users end
        # See https://developer.apple.com/documentation/webkit/testing_with_webdriver_in_safari
        driver = webdriver.Safari(options=options)
    else:
        if platform == "linux" or platform == "linux2":
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--remote-debugging-port=9222")

        options.add_argument("--no-sandbox")
        if CFG.selenium_headless:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")

        driver = webdriver.Chrome(
            executable_path=ChromeDriverManager().install(), options=options
        )

    return driver

def scrape_text_with_selenium(url: str, driver) -> tuple[WebDriver, str]:
    """Scrape text from a website using selenium

    Args:
        url (str): The url of the website to scrape

    Returns:
        Tuple[WebDriver, str]: The webdriver and the text scraped from the website
    """

    driver.get(url)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    # Get the HTML content directly from the browser's DOM
    page_source = driver.execute_script("return document.body.outerHTML;")
    soup = BeautifulSoup(page_source, "html.parser")

    for script in soup(["script", "style"]):
        script.extract()

    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = "\n".join(chunk for chunk in chunks if chunk)
    return driver, text


def scrape_links_with_selenium(driver: WebDriver, url: str) -> list[str]:
    """Scrape links from a website using selenium

    Args:
        driver (WebDriver): The webdriver to use to scrape the links

    Returns:
        List[str]: The links scraped from the website
    """
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, "html.parser")

    for script in soup(["script", "style"]):
        script.extract()

    hyperlinks = extract_hyperlinks(soup, url)

    return format_hyperlinks(hyperlinks)


def close_browser(driver: WebDriver) -> None:
    """Close the browser

    Args:
        driver (WebDriver): The webdriver to close

    Returns:
        None
    """
    driver.quit()


def add_header(driver: WebDriver) -> None:
    """Add a header to the website

    Args:
        driver (WebDriver): The webdriver to use to add the header

    Returns:
        None
    """
    driver.execute_script(open(f"{FILE_DIR}/js/overlay.js", "r").read())
