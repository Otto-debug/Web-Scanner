import asyncio
import aiohttp

import json

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from scanner.logger import setup_logger
from scanner.payloads import PAYLOADS
from scanner.path import LOGS_DIR, REPORTS_DIR

from fake_useragent import UserAgent

log_path = LOGS_DIR / 'security.log'
report_path = REPORTS_DIR / 'security_report.json'

class SecurityScanner:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.found_vulns = [] # Список найденных уязов
        self.payloads = PAYLOADS
        self.logger = setup_logger(name='security_scanner', log_file=log_path)

    async def fetch(self, session: aiohttp.ClientSession, url: str) -> str:
        """Выполняет GET-запрос"""
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    self.logger.warning(f"Нестандартный код: {response.status} при запросе к {url}")
                text = await response.text()
                return text
        except Exception as e:
            self.logger.warning(f"Ошибка при запросе {url}: {e}")
            return ""

    def injected_payload(self, url: str, payload: str) -> str:
        """Подставляет указанный payload во все параметры запроса URL
           Возвращает изменённый URL."""
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        injected = {k: payload for k in query} # Все параметры получают один и тот же payload
        new_query = urlencode(injected, doseq=True)
        return urlunparse(parsed._replace(query=new_query))

    # async def test_vulnerabilities(self, session: aiohttp.ClientSession, url: str):
    #     """Проверяет указанный URL на XSS и SQLi уязвимости, внедряя тестовые payload и анализирует ответ"""
    #
    #     for vuln_type, payload in self.payloads.items():
    #         test_url = self.injected_payload(url, payload)
    #         response = await self.fetch(session, test_url)
    #
    #         # Проверка на XSS
    #         if vuln_type == 'xss' and payload in response:
    #             self.found_vulns.append({
    #                 'type': 'XSS',
    #                 'url': test_url,
    #                 'payload': payload
    #             })
    #             self.logger.warning(f"XSS обнаружен на: {test_url}")
    #
    #         # Проверка на SQL-инъекции - по наличию характерных ошибок в HTML-ответе
    #         elif vuln_type == 'sqli' and any(err in response.lower() for err in ['sql syntax', 'mysql', 'warning']):
    #             self.found_vulns.append({
    #                 'type': 'SQLi',
    #                 'url': test_url,
    #                 'payload': payload
    #             })
    #             self.logger.warning(f'SQL-инъекция найдена на: {test_url}')

    async def test_vulnerabilities(self, session: aiohttp.ClientSession, url: str):
        """Проверяет указанный URL на XSS и SQLi уязвимости, внедряя тестовые payload и анализирует ответ"""

        for vuln_type, payload_list in self.payloads.items():
            for payload in payload_list:
                test_url = self.injected_payload(url, payload)
                response = await self.fetch(session, test_url)

                # Проверка на XSS
                if vuln_type == 'xss' and payload in response:
                    self.found_vulns.append({
                        'type': 'XSS',
                        'url': test_url,
                        'payload': payload
                    })
                    self.logger.warning(f"XSS обнаружен на: {test_url}")

                # Проверка на SQL-инъекции - по наличию характерных ошибок в HTML-ответе
                elif vuln_type == 'sqli' and any(err in response.lower() for err in
                                                 ['sql syntax', 'mysql', 'warning', 'unterminated',
                                                  'error in your SQL']):
                    self.found_vulns.append({
                        'type': 'SQLi',
                        'url': test_url,
                        'payload': payload
                    })
                    self.logger.warning(f'SQL-инъекция найдена на: {test_url}')

    async def run(self, urls_with_params: list[str]):
        """Запускает асинхронное сканирование"""
        ua = UserAgent()
        headers = {'User-Agent': ua.random}
        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            tasks = [self.test_vulnerabilities(session, url) for url in urls_with_params]
            await asyncio.gather(*tasks)

        self.logger.info(f"Найдено потенциальных уязвимостей: {len(self.found_vulns)}")

        for vuln in self.found_vulns:
            print(vuln)

        return self.found_vulns

    def save_report_json(self, filename: str=report_path):
        """Отчёт в JSON"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.found_vulns, f, indent=4, ensure_ascii=False)

        self.logger.info(f"Отчёт сохранён в: {filename}")



