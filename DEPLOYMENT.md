# Инструкции по развертыванию Health Monitor Bot

## Настройка CI/CD с GitHub Actions

### 1. Настройка GitHub Runner на сервере

1. Перейдите в настройки репозитория: Settings → Actions → Runners
2. Нажмите "New self-hosted runner"
3. Выберите операционную систему вашего сервера
4. Следуйте инструкциям для установки и настройки runner'а

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```bash
cp env.example .env
```

Заполните файл `.env` реальными значениями:

```env
TOKEN=your_actual_telegram_bot_token
```

### 3. Настройка GitHub Secrets (рекомендуется)

Для безопасности используйте GitHub Secrets:

1. Перейдите в Settings → Secrets and variables → Actions
2. Добавьте следующие секреты:
   - `TELEGRAM_BOT_TOKEN` - токен вашего бота

### 4. Автоматическое развертывание

После настройки runner'а и переменных окружения:

1. Сделайте push в ветку `main` или `master`
2. GitHub Actions автоматически:
   - Запустит тесты с помощью `uv`
   - Соберет Docker образ с `uv`
   - Развернет приложение на вашем сервере

### 5. Мониторинг

Проверьте статус развертывания:

```bash
# Статус контейнеров
docker-compose ps

# Логи приложения
docker-compose logs -f app

# Проверка здоровья
docker-compose exec app uv run python -c "import requests; print('Bot is healthy')"
```

### 6. Обновление

Для обновления приложения просто сделайте push в main ветку - GitHub Actions автоматически обновит приложение:

```bash
git add .
git commit -m "Update bot"
git push origin main
```

## Структура проекта

```
health_monitor_tg_bot/
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions workflow
├── app/                        # Исходный код приложения
├── tests/                      # Тесты
├── docker-compose.yml          # Docker Compose конфигурация
├── Dockerfile                  # Docker образ с uv
├── pyproject.toml              # Конфигурация uv
├── uv.lock                     # Lock файл uv
├── env.example                 # Пример переменных окружения
└── requirements.txt            # Python зависимости (legacy)
```

## Устранение неполадок

### Проблемы с Docker

```bash
# Очистка Docker
docker system prune -a

# Пересборка образов
docker-compose build --no-cache
```

### Проблемы с правами доступа

```bash
# Исправление прав на файлы
chmod 644 .env
```

### Проблемы с базой данных

```bash
# Проверка базы данных
docker-compose exec app ls -la /app/measurements.db

# Создание резервной копии
docker-compose exec app cp /app/measurements.db /app/measurements.db.backup
```
