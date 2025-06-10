# 🕷 Web-Scanner

**Web-Scanner** — это асинхронный Python-сканер сайтов, который выполняет базовый SEO-анализ, проверяет битые ссылки, собирает данные о структуре страниц и может формировать HTML-отчёты.

## 📦 Возможности

- 🔍 Асинхронный обход сайта (BFS)
- 🔍 Проверка XSS и SQLi уязвимостей
- 🔗 Проверка битых ссылок
- 🏷 Сбор метаданных:
  - Заголовки `title`, `h1-h6`
  - Внутренние / внешние ссылки
  - Количество скриптов, стилей и изображений
- ⚙️ Учет правил `robots.txt` и `meta robots`
- 🧾 Генерация JSON и HTML-отчётов
- 🐳 Поддержка Docker

---

## 🚀 Установка и запуск
- python3 -m venv .venv
- source .venv/bin/activate
- pip install -r requirements.txt
- python3 speed_script.py

### 1. Клонирование проекта

```bash
git clone https://github.com/Otto-Debug/Web-Scanner.git
cd Web-scanner
```

### 2. Docker
- Сборка образа: docker build -t web-scanner .
- Запуск контейнера: docker run --rm web-scanner