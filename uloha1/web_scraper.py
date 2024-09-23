'''
    Web scraper that scrapes idnes.cz articles in parallel using ThreadPoolExecutor.
'''

import concurrent.futures
import re
import bs4
import time
import json
from lxml import html
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--log-level=3,")
chrome_options.add_argument('--ignore-certificate-errors-spki-list')
chrome_options.add_argument('--ignore-ssl-errors')
chrome_options.page_load_strategy = "eager"
CHROME_DRIVER_PATH = './uloha1/chromedriver.exe'
service = Service(CHROME_DRIVER_PATH)
ARTICLES = []
DATAS = []
def scrape_url_articles(url):
    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(url)
        time.sleep(3)
        link = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "Souhlasím")]'))
        )
        link.click()
    except Exception as e:
        pass
    WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//a[@class="art-link"]'))
    )
    html = driver.page_source
    driver.quit()
    soup = bs4.BeautifulSoup(html, 'html.parser')
    new_links = soup.find_all('a', class_='art-link')
    for ref in new_links:
        ARTICLES.append(ref.get('href'))
    return ARTICLES

def scrape_article(url):
    """
    Scrapes an article from the given URL.

    This function uses Selenium WebDriver to open the specified URL, interact with
    the webpage to accept cookies, and then waits for the article link to be present.
    Once the article link is found, it retrieves the page source and parses it using
    BeautifulSoup to extract the desired data.

    Args:
        url (str): The URL of the article to scrape.

    Returns:
        None: The function does not return a value. The scraped data is appended to
        the global DATAS list.
    """
    print("Scraping article: ", str(url))
    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(url)
        time.sleep(3)
        link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "Souhlasím")]'))
        )
        link.click()
    except Exception as e:
        pass
    WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//a[@class="art-link"]'))
        )
    html_source = driver.page_source
    current_url = driver.current_url
    driver.quit()
    parser = html.fromstring(html_source)
    data = get_json(parser,current_url)
    DATAS.append(data)

class Article:
    """
    A class used to represent an Article.
    Attributes
    ----------
    title : str
        The title of the article.
    content : str
        The content of the article.
    category : str
        The category to which the article belongs.
    photos : int
        The number of photos in the article.
    date : str
        The publication date of the article.
    comments : int
        The number of comments on the article.
    Methods
    -------
    json():
        Returns a dictionary representation of the article.
    __str__():
        Returns a string representation of the article.
    """
    def __init__(self,title:str,content:str,category:str,photos:int,date:str,comments:int) -> None:
        self.title = title
        self.content = content
        self.category = category
        self.photos = photos
        self.date = date
        self.comments = comments#dodelat
    def get_json(self):
        return {
        "title": self.title,
        "content": self.content,
        "category": self.category,
        "photos": self.photos,
        "date": self.date,
        "comments": self.comments
        }
    def strip_output(self):
        self.title = self.title.strip()
        self.content = self.content.strip()
        self.category = self.category.strip()
        self.date = self.date.strip()
    def __str__(self) -> str:
        return f"Title: {self.title}\nContent: {self.content}\nCategory: {self.category}\nPhotos: {self.photos}\nDate: {self.date}\nComments: {self.comments}"

def get_json(parser:html.fromstring,html_source:str):
    # Extract the title using XPath
    title = parser.xpath('//*[@id="space-a"]/div/h1/text()')[0]
    content_opener = parser.xpath('//*[@id="space-a"]/div/div[2]/text()')[0]
    content = content_opener+parser.xpath('//*[@id="space-b"]/div/div[1]/text()')[0]
    category = html_source.split("/")[3]
    photos = parser.xpath('//div[@id="space-b"]//descendant::img')
    photos = len(photos)
    date = parser.xpath('//*[@id="space-a"]/div/div[1]/div[1]/div/span/span[1]/text()')[0]
    comments = parser.xpath('//*[@id="moot-linkin"]/span/text()')[0]
    comments = int(re.findall(r'\d+', comments)[0])
    article = Article(title,content,category,photos,date,comments)
    article.strip_output()
    return article.get_json()

url_list = ["https://www.idnes.cz/sport/archiv/"+str(index) for index in range(1, 18)]

def scrape_in_parallel_articles(urls, max_threads):
    art_datas = []
    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        art_datas = {executor.submit(scrape_article, url): url for url in urls}
    return art_datas
def scrape_in_parallel(urls, max_threads):
    with concurrent.futures.ThreadPoolExecutor(max_threads) as executor:
        articles = {executor.submit(scrape_url_articles, url): url for url in urls}
    return articles

if __name__ == '__main__':
    time_start = time.time()
    MAX_THREADS = 8
    scraped_titles = scrape_in_parallel(url_list, MAX_THREADS)
    scraped_articles = scrape_in_parallel_articles(ARTICLES, MAX_THREADS)
    print(DATAS)
    with open('datas.json', 'w', encoding='utf-8') as f:
        json.dump(DATAS, f, ensure_ascii=False, indent=4)
    time_end = time.time()
    print(f"Scraping took {time_end - time_start} seconds")
    print(f"Total number of articles scraped: {len(DATAS)}")
    