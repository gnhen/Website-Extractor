import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time

visited_urls = set()


def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)


def save_content(url, folder):
    response = requests.get(url)
    filename = os.path.join(
        folder, os.path.basename(urlparse(url).path) or "index.html"
    )

    with open(filename, "wb") as file:
        file.write(response.content)
    print(f"Downloaded: {url}")


def crawl_and_download(url, base_folder, depth=2):
    if depth == 0 or url in visited_urls:
        return
    visited_urls.add(url)

    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        save_content(url, base_folder)

        for link in soup.find_all("a", href=True):
            link_url = urljoin(url, link["href"])
            if urlparse(link_url).netloc == urlparse(url).netloc:
                crawl_and_download(link_url, base_folder, depth - 1)

        for resource_tag, attr in [("img", "src"), ("script", "src"), ("link", "href")]:
            for resource in soup.find_all(resource_tag, {attr: True}):
                resource_url = urljoin(url, resource[attr])
                if resource_url not in visited_urls:
                    visited_urls.add(resource_url)
                    save_content(resource_url, base_folder)

    except Exception as e:
        print(f"Failed to download {url}: {e}")


if __name__ == "__main__":
    website_url = input("Enter the website URL: ")
    base_folder = "downloaded_site"

    create_directory(base_folder)
    crawl_and_download(website_url, base_folder)
