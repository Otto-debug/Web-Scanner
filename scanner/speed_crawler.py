import asyncio
import json
import os

from datetime import datetime

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from collections import deque

from scanner.logger import setup_logger
from scanner.path import LOGS_DIR, REPORTS_DIR


# robot.txt парсер
from urllib.robotparser import RobotFileParser

log_path = LOGS_DIR / 'scanner.log'
report_path = REPORTS_DIR / 'async2_structure.json'

class AsyncWebCrawler:
    def __init__(self, base_url: str, max_pages: int = 100):
        self.base_url = base_url.rstrip("/") # Удаляем конечный слеш для консистентности
        self.visited = set() # Множество посещённых URL
        self.results = [] # Список с данными по каждой странице
        self.max_pages = max_pages # Лимит на кол-во сканируемых страниц
        self.broken_links = () # Кол-во битых ссылок
        self.checked_links = {} # Кэш для проверенных ссылок
        self.logger = setup_logger(name='web_scanner', log_file=log_path) # Логгер
        self.sem = asyncio.Semaphore(10) # Семафор - макс. 10 параллельных запросов
        self.robots_parser = RobotFileParser()
        self.robots_parser = None
        self.robots_loaded = False

    def is_internal_link(self, link: str) -> bool:
        """Проверяет, является ли ссылка внутренней"""
        return urlparse(link).netloc == urlparse(self.base_url).netloc

    async def fetch_html(self, session: ClientSession, url: str) -> str | None:
        """Асинхронно загружает HTML страницу"""
        try:
            async with self.sem:
                async with session.get(url, timeout=ClientTimeout(total=5)) as response:
                    if 'text/html' in response.headers.get("Content-Type", ""):
                        return await response.text()
        except Exception as e:
            self.logger.warning(f"[HTML] Ошибка при загрузке {url}: {e}")
        return None

    def obey_robots_txt(self, url: str) -> bool:
        """Проверка, разрешён ли URL по robots.txt"""
        if self.robots_parser is None or not self.robots_loaded:
            return True
        return self.robots_parser.can_fetch("*", url)

    async def load_robots_txt(self, session: ClientSession):
        """Загрузка и парсинг robots.txt"""
        robots_url = urljoin(self.base_url, "/robots.txt")
        try:
            async with session.get(robots_url) as response:
                if response.status == 200:
                    content = await response.text()
                    self.robots_parser = RobotFileParser()
                    self.robots_parser.parse(content.splitlines())
                    self.robots_loaded = True
                    self.logger.info("robots.txt успешно загружен")
                else:
                    self.logger.warning("robots.txt не найден или недоступен")
                    self.robots_parser = None
                    self.robots_loaded = False
        except Exception as e:
            self.logger.warning(f"Ошибка при загрузке robots.txt: {e}")
            self.robots_parser = None
            self.robots_loaded = False

    async def check_link_status(self, session: ClientSession, url: str) -> int | None:
        """Асинхронно, проверяет статус ссылки с кэшированием"""
        if url in self.checked_links:
            return self.checked_links[url]

        try:
            async with self.sem:
                async with session.head(url, allow_redirects=True, timeout=ClientTimeout(total=3)) as response:
                    self.checked_links[url] = response.status
                    return response.status
        except Exception:
            self.checked_links[url] = None
            return None

    async def analyze_page(self, session: ClientSession, url: str, html: str) -> tuple[dict, set[str]]:
        """Парсит HTML: извлекает заголовки, теги и ссылки,
            а также классифицирует их"""
        soup = BeautifulSoup(html, 'html.parser')

        # Подсчёт заголовков
        headings = {
            f"h{i}": len(soup.find_all(f"h{i}")) for i in range(1, 7)
        }

        internal_links = set()
        external_links = set()

        all_links = soup.find_all("a", href=True)

        # Асинхронно обрабатываем ссылки на странице
        tasks = []
        for tag in all_links:
            link = urljoin(url, tag["href"]).split('#')[0].rstrip('/')
            tasks.append(self.process_link(session, url, link, internal_links, external_links))

        await asyncio.gather(*tasks)

        result = {
            "url": url,
            "title": soup.title.string.strip() if soup.title and soup.title.string else "No title",
            "structure": {
                "headings": headings,
                "images": len(soup.find_all("img")),
                "scripts": len(soup.find_all("script")),
                "stylesheets": len(soup.find_all("link", rel="stylesheet")),
                "internal_links": len(internal_links),
                "external_links": len(external_links)
            }
        }
        return result, internal_links

    async def process_link(self, session, source_url, link, internal_links, external_links):
        """
        Асинхронно проверяет статус и классифицирует её внутреннюю или внешнюю.
        Так же фиксирует битую ссылку
        """
        status = await self.check_link_status(session, link)
        if status and status >= 400:
            # self.broken_links.append({
            #     "source": source_url,
            #     "link": link,
            #     "status": status
            # })
            self.broken_links.add((source_url, link, status))

        if self.is_internal_link(link):
            internal_links.add(link)
        else:
            external_links.add(link)

    def extract_meta_robots(self, soup: BeautifulSoup) -> dict:
        """Извлекает meta name='robots' и возвращает дерективы"""
        meta_tag = soup.find("meta", attrs={"name": "robots"})
        if not meta_tag or not meta_tag.get("content"):
            return {"index": True, "follow": True}

        content = meta_tag["content"].lower()
        return {
            "index": "noindex" not in content,
            "follow": "nofollow" not in content
        }

    def extract_seo_warnings(self, soup: BeautifulSoup, url: str) -> list[str]:
        """Примитивный SEO-анализ страниц"""
        warnings = []

        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        if not title:
            warnings.append("Отсутствует <title>")
        elif len(title) > 60:
            warnings.append(f"Title слишком длинный: {len(title)} символов")

        description = soup.find("meta", attrs={"name": "description"})
        if not description or not description.get("content"):
            warnings.append("Отсутствует meta description")

        h1_tags = soup.find_all("h1")
        if len(h1_tags) == 0:
            warnings.append("Нет <h1> на странице")
        elif len(h1_tags) > 1:
            warnings.append("Больше одного <h1> на странице")

        images = soup.find("img")
        for img in images:
            if not img.get("alt"):
                warnings.append("Найдены <img> без alt")
                break

        return warnings

    async def crawl(self):
        """Основной метод сканирования. Используем очередь для обхода в ширину(BFC)"""
        queue : deque[str] = deque([self.base_url])
        pages_processed = 0

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/114 Safari/537.36"
        }

        async with ClientSession(headers=headers, connector=TCPConnector(ssl=False)) as session:
            await self.load_robots_txt(session)

            while queue and pages_processed < self.max_pages:
                url = queue.popleft()
                url = url.split('#')[0].rstrip('/')

                if url in self.visited:
                    continue

                if not self.obey_robots_txt(url):
                    self.logger.info(f"[robots.txt] Пропущен: {url}")

                html = await self.fetch_html(session, url)
                if not html:
                    continue

                self.visited.add(url)
                analysis, new_links = await self.analyze_page(session, url, html)
                self.results.append(analysis)
                pages_processed += 1

                self.logger.info(f"[{pages_processed}] Обработано: {url}")
                print(f'[{pages_processed}] Обработано: {url}')

                # Добавление новых внутренних ссылок в очередь
                for link in new_links:
                    clean_link = link.split("#")[0].rstrip('/')
                    if clean_link not in self.visited:
                        queue.append(clean_link)

            self.logger.info(f"Сканирование завершено. Всего страниц: {pages_processed}")
            print(f"Сканирование завершено. Всего страниц: {pages_processed}")

    def save_html_report(self, filename: str = report_path):
        """Генерация HTML-отчёта"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = [
            "<!DOCTYPE html>",
            "<html lang='ru'>",
            "<head>",
            "<meta charset='UTF-8'>",
            "<title>Отчёт по сканированию сайта</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; padding: 20px; }",
            "table { width: 100%; border-collapse: collapse; margin-bottom: 40px; }",
            "th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }",
            "th { background-color: #f2f2f2; }",
            "h2 { margin-top: 40px; }",
            "</style>",
            "</head>",
            "<body>",
            f"<h1>Отчёт по сканированию сайта</h1>",
            f"<p><strong>Дата:</strong> {now}</p>",
            f"<p><strong>Сайт:</strong> {self.base_url}</p>",
            f"<p><strong>Просканировано страниц:</strong> {len(self.results)}</p>",
            "<h2>Список страниц</h2>",
            "<table>",
            "<tr><th>URL</th><th>Заголовок</th><th>H1-H6</th><th>Картинок</th><th>Скриптов</th><th>Стили</th><th>Вн. ссылки</th><th>Внеш. ссылки</th></tr>"
        ]

        for page in self.results:
            s = page['structure']
            headings_summary = ", ".join(f"{k}: {v}" for k, v in s['headings'].items() if v > 0)
            html.append(
                f"<tr><td>{page['url']}</td>"
                f"<td>{page['title']}</td>"
                f"<td>{headings_summary}</td>"
                f"<td>{s['images']}</td>"
                f"<td>{s['scripts']}</td>"
                f"<td>{s['stylesheets']}</td>"
                f"<td>{s['internal_links']}</td>"
                f"<td>{s['external_links']}</td></tr>"
            )

        html.append("</table>")  # Закрываем таблицу страниц


        html.append("<h2>Битые ссылки</h2>")
        if self.broken_links:
            html.append("<table>")
            html.append("<tr><th>Источник</th><th>Битая ссылка</th><th>Статус</th></tr>")
            for source, link, status in self.broken_links:
                html.append(f"<tr><td>{source}</td><td>{link}</td><td>{status}</td></tr>")
            html.append("</table>")
        else:
            html.append("<p>Битые ссылки не найдены.</p>")

        html.append("</body></html>")  # Закрываем HTML

        with open(filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(html))

        self.logger.info(f"HTML-отчёт сохранён в {filename}")
        print(f"HTML-отчёт сохранён в: {filename}")

    def save_results(self, filename: str = report_path):
        """
        Сохраняет результаты сканирования.
        """
        result_data = {
            "pages": self.results,
            "broken_links": self.broken_links
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Отчёт сохранён в: {filename}")
        print(f'Отчёт сохранён в: {filename}')