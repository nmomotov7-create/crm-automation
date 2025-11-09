# Базовый образ Python 3.14
FROM python:3.14-slim

# Установка Chromium и chromedriver
RUN apt-get update && \
    apt-get install -y chromium chromium-driver && \
    rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . /app
WORKDIR /app

# Экспонируем порт для Render
EXPOSE 5000

# Запуск Flask
CMD ["python", "crm_webhook.py"]
