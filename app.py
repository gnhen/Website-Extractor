import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import random
import argparse
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import undetected_chromedriver as uc  # Updated import for undetected-chromedriver

# Configure logging
logging.basicConfig(
    filename="crawler.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

visited_urls = set()

# Expanded list of user agents for better variability
USER_AGENTS = [
    # Desktop User Agents
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/115.0.0.0 Safari/537.36",
    # Mobile User Agents
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/15.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/115.0.0.0 Mobile Safari/537.36",
    # Add more user agents as needed
]

# Configure session with retries
session = requests.Session()
retries = Retry(
    total=10,  # Increased from 5 to 10
    backoff_factor=3,  # Increased from 2 to 3
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"],  # Specify allowed methods
)
session.mount("http://", HTTPAdapter(max_retries=retries))
session.mount("https://", HTTPAdapter(max_retries=retries))


def get_random_user_agent():
    return random.choice(USER_AGENTS)


def create_directory(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace(".", "_")
    scheme = parsed_url.scheme
    folder_name = f"{scheme}_{domain}"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        logging.info(f"Created directory: {folder_name}")
    return folder_name


def get_selenium_driver():
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument("--headless")  # Remove or comment out for debugging
    chrome_options.add_argument(f"user-agent={get_random_user_agent()}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    # Additional stealth options handled by undetected-chromedriver
    # Removed unsupported 'excludeSwitches' and 'useAutomationExtension'

    try:
        driver = uc.Chrome(options=chrome_options)
        # Further stealth configurations
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            """
            },
        )
        return driver
    except Exception as e:
        logging.error(f"Error initializing Selenium WebDriver: {e}")
        return None


def save_content_selenium(url, folder):
    driver = get_selenium_driver()
    if not driver:
        logging.error(f"Selenium driver not available for {url}")
        return

    try:
        driver.get(url)
        time.sleep(random.uniform(5, 10))  # Wait for JavaScript to load
        content = driver.page_source

        filename = os.path.join(
            folder, os.path.basename(urlparse(url).path) or "index.html"
        )

        if not os.path.splitext(filename)[1]:
            filename += ".html"

        with open(filename, "w", encoding="utf-8") as file:
            file.write(content)
        logging.info(f"Downloaded with Selenium: {url}")

    except Exception as e:
        logging.error(f"Error downloading with Selenium {url}: {e}")

    finally:
        try:
            driver.quit()
        except Exception as e:
            logging.error(f"Error quitting Selenium driver: {e}")


def save_content(url, folder):
    try:
        headers = {
            "User-Agent": get_random_user_agent(),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.google.com/",
            "DNT": "1",  # Do Not Track
        }
        session.headers.update(headers)

        # Add random delay to mimic human browsing
        time.sleep(random.uniform(5, 15))

        response = session.get(url, timeout=10)
        response.raise_for_status()

        filename = os.path.join(
            folder, os.path.basename(urlparse(url).path) or "index.html"
        )

        if not os.path.splitext(filename)[1]:
            filename += ".html"

        with open(filename, "wb") as file:
            file.write(response.content)
        logging.info(f"Downloaded: {url}")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logging.warning(f"403 Forbidden for {url}. Attempting with Selenium.")
            # Fallback to Selenium
            save_content_selenium(url, folder)
        else:
            logging.error(f"HTTP error downloading {url}: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading {url}: {e}")
        # Fallback to Selenium
        save_content_selenium(url, folder)


def crawl_and_download(url, depth=2):
    if depth == 0 or url in visited_urls:
        return

    visited_urls.add(url)

    folder = create_directory(url)
    logging.info(f"Crawling URL: {url} | Depth: {depth} | Folder: {folder}")
    save_content(url, folder)

    try:
        # Additional headers for crawling
        headers = {
            "User-Agent": get_random_user_agent(),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.google.com/",
            "DNT": "1",
        }
        session.headers.update(headers)

        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            next_url = urljoin(url, link["href"])
            parsed_next = urlparse(next_url)
            if parsed_next.scheme in ["http", "https"]:
                # Avoid crawling the same URL
                if next_url not in visited_urls:
                    crawl_and_download(next_url, depth - 1)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logging.warning(f"403 Forbidden while crawling {url}. Skipping.")
        else:
            logging.error(f"HTTP error crawling {url}: {e}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error crawling {url}: {e}")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Web Crawler")
    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        default=2,
        help="Depth of crawling (default: 2).",
    )
    parser.add_argument(
        "start_url",
        nargs="?",
        default=None,
        help="The starting URL for the crawler.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    start_url = args.start_url
    if not start_url:
        start_url = input("Enter the starting URL: ").strip()
    crawl_depth = args.depth

    crawl_and_download(start_url, depth=crawl_depth)
