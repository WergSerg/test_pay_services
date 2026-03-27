Вот полный README.md для вашего платежного сервиса:
# Payment Processing Service

Асинхронный микросервис для обработки платежей с гарантированной доставкой событий через Outbox pattern, поддержкой идемпотентности и Dead Letter Queue.

## Оглавление

- [Архитектура](#архитектура)
- [Технологии](#технологии)
- [Требования](#требования)
- [Быстрый старт](#быстрый-старт)
- [API Документация](#api-документация)
- [Тестирование](#тестирование)
- [Мониторинг](#мониторинг)
- [Развертывание](#развертывание)
- [Устранение проблем](#устранение-проблем)

## Архитектура

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│   FastAPI    │────▶│  PostgreSQL │
│             │     │     API      │     │  + Outbox   │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                     │
                           ▼                     ▼
                    ┌──────────────┐     ┌─────────────┐
                    │   Outbox     │     │  RabbitMQ   │
                    │   Worker     │────▶│   Queue     │
                    └──────────────┘     └─────────────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │  Consumer   │
                                         │  Processor  │
                                         └─────────────┘
                                                │
                                    ┌───────────┴───────────┐
                                    ▼                       ▼
                             ┌─────────────┐        ┌─────────────┐
                             │   Webhook   │        │  PostgreSQL │
                             │  Endpoint   │        │   Update    │
                             └─────────────┘        └─────────────┘
```

### Компоненты системы

1. **API сервис** - принимает HTTP запросы на создание и получение платежей
2. **Outbox Worker** - читает outbox таблицу и публикует события в RabbitMQ
3. **Consumer** - обрабатывает платежи, эмулирует работу с платежным шлюзом
4. **PostgreSQL** - основная база данных (таблицы payments и outbox)
5. **RabbitMQ** - брокер сообщений с поддержкой Dead Letter Queue

## 🛠 Технологии

- **Python 3.11** - основной язык
- **FastAPI** - веб-фреймворк
- **SQLAlchemy 2.0** - ORM (асинхронный режим)
- **PostgreSQL** - база данных
- **RabbitMQ** - брокер сообщений
- **Alembic** - миграции
- **Docker & Docker Compose** - контейнеризация
- **Pydantic v2** - валидация данных
- **aio-pika** - асинхронный клиент RabbitMQ
- **tenacity** - retry логика

## Требования

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+ (для локальной разработки)
- Make (опционально)

##  Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/yourusername/payment-service.git
cd payment-service
```

### 2. Настройка окружения

```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Отредактируйте .env при необходимости
nano .env
```

### 3. Запуск сервисов

```bash
# Запустить все сервисы
docker-compose up -d

# Проверить статус
docker-compose ps

# Посмотреть логи
docker-compose logs -f
```

### 4. Применение миграций

```bash
# Запустить миграции
docker-compose exec api alembic upgrade head

# Проверить таблицы
docker-compose exec postgres psql -U postgres -d payments_db -c "\dt"
```

### 5. Проверка работоспособности

```bash
# Health check
curl http://localhost:8000/health/

# Должны получить:
# {"status":"healthy"}
```

##  API Документация

### Аутентификация

Все эндпоинты требуют API ключ в заголовке `X-API-Key`:

```
X-API-Key: your-api-key
```

### Эндпоинты

#### 1. Создание платежа

**POST** `/api/v1/payments`

**Заголовки:**
- `X-API-Key`: API ключ (обязательный)
- `Idempotency-Key`: Уникальный ключ для защиты от дублей (обязательный)

**Тело запроса:**
```json
{
  "amount": 1000.50,
  "currency": "RUB",
  "description": "Оплата заказа #123",
  "webhook_url": "https://your-domain.com/webhook",
  "metadata_json": {
    "order_id": "order-123",
    "customer_id": 456
  }
}
```

**Ответ (202 Accepted):**
```json
{
  "id": "fdb8f1e1-b077-49ff-a577-c42f4283418b",
  "status": "pending",
  "created_at": "2026-03-27T12:26:17.682703Z",
  "amount": "1000.50",
  "currency": "RUB",
  "description": "Оплата заказа #123",
  "metadata_json": {
    "order_id": "order-123",
    "customer_id": 456
  },
  "webhook_url": "https://your-domain.com/webhook",
  "processed_at": null
}
```

#### 2. Получение информации о платеже

**GET** `/api/v1/payments/{payment_id}`

**Заголовки:**
- `X-API-Key`: API ключ (обязательный)

**Ответ (200 OK):**
```json
{
  "id": "fdb8f1e1-b077-49ff-a577-c42f4283418b",
  "idempotency_key": "unique-key-123",
  "status": "succeeded",
  "created_at": "2026-03-27T12:26:17.682703Z",
  "processed_at": "2026-03-27T12:26:23.123456Z",
  "amount": "1000.50",
  "currency": "RUB",
  "description": "Оплата заказа #123",
  "metadata_json": {
    "order_id": "order-123",
    "customer_id": 456
  },
  "webhook_url": "https://your-domain.com/webhook"
}
```

#### 3. Health Check

**GET** `/health/`

**Ответ (200 OK):**
```json
{
  "status": "healthy"
}
```

### Статусы платежей

- `pending` - платеж создан, ожидает обработки
- `succeeded` - платеж успешно обработан
- `failed` - платеж отклонен

### Webhook уведомления

После обработки платежа отправляется POST запрос на указанный URL:

```json
{
  "payment_id": "fdb8f1e1-b077-49ff-a577-c42f4283418b",
  "status": "succeeded",
  "amount": 1000.50,
  "currency": "RUB",
  "description": "Оплата заказа #123",
  "processed_at": "2026-03-27T12:26:23.123456Z",
  "metadata_json": {
    "order_id": "order-123",
    "customer_id": 456
  }
}
```

**Политика retry:**
- 5xx ошибки сервера: 3 попытки с экспоненциальной задержкой
- 4xx ошибки клиента: без retry
- 429 Too Many Requests: retry с увеличенной задержкой

## Тестирование

### Ручное тестирование API

```bash
# Запустить тестовый скрипт
chmod +x test_api.sh
./test_api.sh
```

## Мониторинг

### Проверка очередей RabbitMQ

```bash
# Список очередей
docker exec $(docker ps -qf "name=rabbitmq") rabbitmqctl list_queues

# Детальная информация
docker exec $(docker ps -qf "name=rabbitmq") rabbitmqctl list_queues name messages_ready messages_unacknowledged consumers
```

### Мониторинг базы данных

```sql
-- Статистика по платежам
SELECT status, COUNT(*) FROM payments GROUP BY status;

-- Статистика outbox
SELECT status, COUNT(*) FROM outbox GROUP BY status;

-- Зависшие платежи (pending > 5 минут)
SELECT * FROM payments 
WHERE status = 'pending' 
AND created_at < NOW() - INTERVAL '5 minutes';
```

### Мониторинг webhook в реальном времени

```bash
# Запустить мониторинг webhook
./monitor_webhooks.sh
```

### Логи

```bash
# Логи API
docker-compose logs -f api

# Логи outbox worker
docker-compose logs -f worker

# Логи consumer
docker-compose logs -f consumer
```

##  Развертывание

### Производственное окружение
1. **Скопировать файл с переменными окружения:**
```bash
cp .env.example .env
```

2. **Измените пароли в .env:**
```bash
POSTGRES_PASSWORD=strong-password
RABBITMQ_PASSWORD=strong-password
API_KEY=your-secret-api-key
```

3. **Настройте базу данных:**
```bash
# Создайте резервную копию перед миграциями
docker-compose exec postgres pg_dump -U postgres payments_db > backup.sql

# Примените миграции
docker-compose exec api alembic upgrade head
```

4. **Настройте мониторинг:**
```yaml
# Добавьте healthcheck в docker-compose.yml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Масштабирование

```bash
# Запустить несколько экземпляров consumer
docker-compose up -d --scale consumer=3

# Запустить несколько экземпляров API
docker-compose up -d --scale api=2
```

## 🔍 Устранение проблем

### Проблемы с подключением к базе данных

```bash
# Проверьте, что PostgreSQL запущен
docker-compose ps postgres

# Проверьте логи
docker-compose logs postgres

# Проверьте подключение
docker-compose exec postgres pg_isready -U postgres
```

### Outbox сообщения не отправляются

```bash
# Проверьте статус outbox
docker-compose exec postgres psql -U postgres -d payments_db -c "
SELECT status, COUNT(*) FROM outbox GROUP BY status;"

# Проверьте подключение worker к RabbitMQ
docker-compose logs worker | grep "Connected to RabbitMQ"

# Перезапустите worker
docker-compose restart worker
```

### Consumer не обрабатывает сообщения

```bash
# Проверьте, что есть сообщения в очереди
docker exec $(docker ps -qf "name=rabbitmq") rabbitmqctl list_queues | grep payments.new

# Проверьте логи consumer
docker-compose logs consumer | tail -50

# Перезапустите consumer
docker-compose restart consumer
```

### Webhook не отправляются

```bash
# Проверьте, что webhook URL доступен
curl -X POST https://your-webhook-url.com/test

# Проверьте логи consumer
docker-compose logs consumer | grep -i webhook

# Проверьте retry логику
docker-compose logs consumer | grep -i "retry"
```

### Dead Letter Queue (DLQ)

```bash
# Проверить сообщения в DLQ
docker exec $(docker ps -qf "name=rabbitmq") rabbitmqctl list_queues | grep dlq

# Просмотреть содержимое DLQ (требуется дополнительный скрипт)
# Очистить DLQ
docker exec $(docker ps -qf "name=rabbitmq") rabbitmqctl purge_queue payments.new.dlq
```

## Производительность

### Настройка пула соединений

В `config.py`:
```python
pool_size=20,        # Размер пула соединений
max_overflow=10,     # Максимальное количество дополнительных соединений
```

### Настройка outbox worker

```bash
# Интервал опроса outbox (секунды)
OUTBOX_POLL_INTERVAL=2
```

### Настройка consumer

В `payment_consumer.py`:
```python
MAX_RETRIES = 3      # Максимальное количество попыток
WEBHOOK_TIMEOUT = 10 # Таймаут webhook в секундах
```

##  Известные ограничения

1. **Эмуляция платежного шлюза**: 90% успеха, 10% ошибок
2. **Время обработки**: 2-5 секунд (эмуляция)
3. **Retry webhook**: 3 попытки для 5xx ошибок
4. **Idempotency key**: Уникальность проверяется на уровне БД


##  Лицензия

MIT License - см. файл [LICENSE](LICENSE)

##  TODO

- [ ] Добавить Prometheus метрики
- [ ] Интегрировать с Grafana для визуализации
- [ ] Добавить distributed tracing (OpenTelemetry)
- [ ] Реализовать dashboard для мониторинга
- [ ] Добавить support для webhook signature verification
- [ ] Реализовать graceful shutdown для всех сервисов
- [ ] Добавить автоматическое создание индексов в миграциях
