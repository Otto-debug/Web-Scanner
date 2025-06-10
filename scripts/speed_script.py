import asyncio
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scanner.speed_crawler import AsyncWebCrawler

def main():
    url = "https://books.toscrape.com"
    crawler = AsyncWebCrawler(url, max_pages=10)
    asyncio.run(crawler.crawl())
    crawler.save_html_report()
    crawler.save_results()

if __name__ == '__main__':
    main()