import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio

from scanner.security_scanner import SecurityScanner

def main():

    urls = [
        "https://xss-game.appspot.com/level1/frame?query=test"
    ]

    scanner = SecurityScanner(base_url="https://xss-game.appspot.com")
    asyncio.run(scanner.run(urls))
    scanner.save_report_json()

if __name__ == '__main__':
    main()