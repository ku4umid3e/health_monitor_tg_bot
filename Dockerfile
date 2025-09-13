FROM python:3.11-alpine

# Установка системных зависимостей
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    curl

# Установка uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Создание пользователя для безопасности
RUN adduser -D bot-user

# Копирование файлов конфигурации uv
COPY pyproject.toml uv.lock /temp/

# Установка зависимостей с помощью uv
WORKDIR /temp
RUN uv sync --frozen --no-dev

# Копирование исходного кода
COPY app /app
WORKDIR /app

# Создание директории для логов
RUN mkdir -p /app/logs && chown -R bot-user:bot-user /app

# Переключение на непривилегированного пользователя
USER bot-user

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.cargo/bin:$PATH"

# Команда по умолчанию
CMD ["uv", "run", "python", "main.py"]