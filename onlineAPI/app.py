import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import random
import logging
from flask import Flask, request, jsonify
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    filename="crawler.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

visited_urls = set()

# User agents for requests
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
]

# Configure session with retries
session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"],
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


def save_content(url, folder):
    try:
        headers = {
            "User-Agent": get_random_user_agent(),
        }
        session.headers.update(headers)
        time.sleep(random.uniform(1, 3))
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
    except Exception as e:
        logging.error(f"Error downloading {url}: {e}")


def crawl_and_download(url, depth=2):
    if depth == 0 or url in visited_urls:
        return

    visited_urls.add(url)
    folder = create_directory(url)
    save_content(url, folder)

    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a", href=True):
            next_url = urljoin(url, link["href"])
            parsed_next = urlparse(next_url)
            if parsed_next.scheme in ["http", "https"] and next_url not in visited_urls:
                crawl_and_download(next_url, depth - 1)
    except Exception as e:
        logging.error(f"Error crawling {url}: {e}")


@app.route("/start_crawl", methods=["POST"])
def start_crawl():
    data = request.json
    url = data.get("url")
    depth = data.get("depth", 2)

    if not url:
        return jsonify({"error": "URL is required."}), 400

    try:
        crawl_and_download(url, depth)
        return jsonify({"message": "Crawling started", "url": url, "depth": depth})
    except Exception as e:
        logging.error(f"Error starting crawl: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/logs", methods=["GET"])
def get_logs():
    try:
        with open("crawler.log", "r") as log_file:
            logs = log_file.readlines()
        return jsonify({"logs": logs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
