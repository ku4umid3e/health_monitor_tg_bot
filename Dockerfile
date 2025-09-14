FROM python:3.11-alpine
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Установка системных зависимостей
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    curl

# Установка uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Создание пользователя для безопасности
RUN adduser -u 1000 --disabled-password --gecos "" bot-user
ENV PATH="/home/bot-user/.cargo/bin:$PATH"

# Копирование файлов конфигурации uv
COPY pyproject.toml uv.lock /app/

# Установка зависимостей с помощью uv
WORKDIR /app
RUN uv sync --frozen --no-dev

# Копирование исходного кода
COPY app /app

# Создание директорий и установка прав
RUN mkdir -p /app/logs /app/data && chown -R bot-user:bot-user /app

# Переключение на непривилегированного пользователя
USER bot-user

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.local/bin:$PATH"

# Команда по умолчанию
CMD ["uv", "run", "python", "main.py"]
