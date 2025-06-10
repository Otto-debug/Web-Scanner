# Базовый образ
FROM python:3.11-slim

# Устанавливаем зависимости
RUN apt-get update && \
    apt-get install -y build-essential && \
    apt-get clean

# Устанавливаем рабочую директорию
WORKDIR /Web-Scanner

# Копируем зависимости и код
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаём директории для логов и отчётов
RUN mkdir -p logs reports

# Команда по умолчанию
CMD ["python"]