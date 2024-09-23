import concurrent.futures
import re
import time
import json
from lxml import html
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--log-level=3")
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--ignore-ssl-errors')
chrome_options.page_load_strategy = "eager"

class Article:
    def __init__(self, title, content, category, photos, date, comments):
        self.title = title.strip()
        self.content = content.strip()
        self.category = category.strip()
        self.photos = photos
        self.date = date.strip()
        self.comments = comments

    def to_json(self):
        return {
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "photos": self.photos,
            "date": self.date,
            "comments": self.comments
        }

    def __str__(self):
        return f"Title: {self.title}\nContent: {self.content}\nCategory: {self.category}\nPhotos: {self.photos}\nDate: {self.date}\nComments: {self.comments}"


def scrape_url_articles(url):
    """Scrapes article URLs from the archive page."""
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(url)
    time.sleep(0.5)  # Wait for the page to load
    try:
        # Accept cookies
        link = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "Souhlasím")]'))
        )
        link.click()
    except Exception:
        pass  # If no cookie banner, continue

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, '//a[@class="art-link"]'))
    )
    parser = html.fromstring(driver.page_source)
    new_links = parser.xpath('//*[@id="list-art-count"]/div/a/@href')
    driver.quit()
    return new_links


def scrape_article(url):
    """Scrapes data from a single article."""
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(url)
    time.sleep(0.5)  # Wait for the page to load
    try:
        link = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "Souhlasím")]'))
        )
        link.click()
    except Exception:
        pass

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, '//h1'))
    )

    parser = html.fromstring(driver.page_source)
    article_data = extract_article_data(parser, driver.current_url)
    driver.quit()
    return article_data


def extract_article_data(parser, current_url):
    """Extracts relevant data from the article's HTML."""
    try:
        title = parser.xpath('//*[@id="space-a"]/div/h1/text()')[0]
        content_opener = parser.xpath('//*[@id="space-a"]/div/div[2]/text()')[0]
        content = content_opener + parser.xpath('//*[@id="space-b"]/div/div[1]/text()')[0]
        category = current_url.split("/")[3]
        photos = len(parser.xpath('//div[@id="space-b"]//descendant::img'))
        date = parser.xpath('//*[@id="space-a"]/div/div[1]/div[1]/div/span/span[1]/text()')[0]
        comments = int(re.findall(r'\d+', parser.xpath('//*[@id="moot-linkin"]/span/text()')[0])[0])

        article = Article(title, content, category, photos, date, comments)
        return article.to_json()
    except (IndexError, AttributeError):
        return None

def scrape_in_parallel(urls, max_threads, scrape_func):
    """Scrapes articles or URLs in parallel using ThreadPoolExecutor."""
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        future_to_url = {executor.submit(scrape_func, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as e:
                print(f"Error scraping {future_to_url[future]}: {e}")
    return results

if __name__ == '__main__':
    start_time = time.time()
    MAX_THREADS = 5  # Adjust according to system capability

    # Step 1: Scrape article URLs from multiple archive pages
    archive_urls = [f"https://www.idnes.cz/sport/archiv/{index}" for index in range(1, 10)]
    all_articles = scrape_in_parallel(archive_urls, MAX_THREADS, scrape_url_articles)
    time.sleep(5)
    # Flatten the list of article URLs
    article_urls = [url for sublist in all_articles for url in sublist]

    # Step 2: Scrape individual articles using the extracted URLs
    article_data = scrape_in_parallel(article_urls, MAX_THREADS, scrape_article)

    # Save the scraped data to a JSON file
    with open('datas.json', 'w', encoding='utf-8') as f:
        json.dump(article_data, f, ensure_ascii=False, indent=4)

    end_time = time.time()
    print(f"Scraping took {end_time - start_time} seconds")
    print(f"Total number of articles scraped: {len(article_data)}")
