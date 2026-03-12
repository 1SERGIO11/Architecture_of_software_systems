# Лабораторная работа №5

**Тема:** Реализация архитектуры на основе сервисов (микросервисной архитектуры)  
**Цель работы:** Получить опыт организации взаимодействия сервисов с использованием контейнеров Docker.

## Описание архитектуры

В рамках лабораторной реализована сервисная архитектура системы заказов сэндвичей с уведомлениями.  
За основу взят API из предыдущей лабораторной работы и адаптирован к работе с PostgreSQL в отдельном контейнере.

Выделены три взаимодействующих контейнера:
- `client` — клиентская часть в виде web UI, доступного в браузере;
- `backend` — серверная часть с REST API;
- `db` — база данных PostgreSQL.

## Состав контейнеров

### Клиентская часть (`client`)
- Назначение: визуальная работа с API в браузере (создание клиентов и заказов, смена статусов, просмотр уведомлений).
- Стек: Nginx + статический frontend (HTML/CSS/JavaScript).
- Основные файлы: `client/Dockerfile`, `client/nginx.conf`, `client/web/index.html`, `client/web/app.js`, `client/web/styles.css`.

### Серверная часть (`backend`)
- Назначение: REST API для работы с клиентами, заказами и уведомлениями.
- Стек: Python 3.12, `http.server`, `psycopg`.
- Основные файлы: `backend/app/api.py`, `backend/app/service.py`, `backend/app/repository.py`, `backend/Dockerfile`.

### База данных (`db`)
- Назначение: постоянное хранение данных клиентов, заказов и уведомлений.
- Стек: PostgreSQL 16 (официальный образ `postgres:16-alpine`).
- Основные параметры: база `sandwich`, пользователь `sandwich`.

## Схема взаимодействия сервисов

![Схема взаимодействия сервисов](img/service_interaction_diagram.svg)

Поток взаимодействия:
1. Клиентский контейнер обращается к endpoint'ам backend.
2. Пользователь работает через web UI, который отправляет REST-запросы к backend.
3. Backend обрабатывает бизнес-логику и выполняет операции чтения/записи в PostgreSQL.
4. Результат возвращается клиенту в JSON-формате.

## Контейнеризация приложения

### Dockerfile backend
- Базовый образ: `python:3.12-slim`.
- Установка зависимостей из `backend/requirements.txt`.
- Копирование серверного приложения в контейнер.
- Точка входа: `python -m app.api`.

### Dockerfile client
- Базовый образ: `nginx:1.27-alpine`.
- Копирование конфигурации `nginx.conf`.
- Копирование frontend-файлов из `client/web/`.
- Публикация интерфейса на порту `8080`.

### docker-compose.yml
Файл `Lab Work №5/docker-compose.yml` описывает:
- сервис `db` с healthcheck `pg_isready`;
- сервис `backend` с переменными окружения подключения к БД и healthcheck endpoint'а `/api/v1/health`;
- сервис `client` с web UI на `http://127.0.0.1:8080`, зависящий от готовности backend.

Дополнительно настроены:
- общая сеть `sandwich-net`;
- том `db_data` для постоянства данных PostgreSQL;
- публикация портов `8001` (backend) и `8080` (client);
- `depends_on` с условием `service_healthy`.

### Переменные окружения backend
- `APP_HOST`, `APP_PORT`
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSLMODE`

## Запуск приложения

Сборка контейнеров:

```bash
docker compose -f "Lab Work №5/docker-compose.yml" build
```

Запуск сервисов:

```bash
docker compose -f "Lab Work №5/docker-compose.yml" up -d
```

Открытие web-клиента:

```bash
open http://127.0.0.1:8080
```

Остановка и удаление сервисов:

```bash
docker compose -f "Lab Work №5/docker-compose.yml" down -v
```

## Проверка работоспособности

### Проверка backend

```bash
curl http://127.0.0.1:8001/api/v1/health
```

Ожидаемый ответ:

```json
{
  "status": "ok",
  "database": "ok"
}
```

### Проверка client

```bash
curl -I http://127.0.0.1:8080
```

Ожидается статус `HTTP/1.1 200 OK`, после чего интерфейс доступен в браузере.

### Проверка PostgreSQL

```bash
docker compose -f "Lab Work №5/docker-compose.yml" exec db psql -U sandwich -d sandwich -c "SELECT COUNT(*) FROM orders;"
```

### Работа через web UI

В интерфейсе доступны операции:
- просмотр списка клиентов через `GET /customers`;
- поиск клиентов по таблице;
- проверка `health` backend;
- создание клиента;
- создание заказа;
- фильтрация списка заказов по `status` и `customer_id`;
- обновление заказа через `PUT`;
- смена статуса через `POST /orders/{id}/status`;
- просмотр уведомлений по заказу;
- удаление заказа через `DELETE`.

Скриншот web UI:

![Web UI Screenshot](img/web_ui_full.png)

## Непрерывная интеграция

Workflow: `.github/workflows/lab5-ci-cd.yml`.

Этапы CI:
1. `checkout` репозитория.
2. Подготовка Python-окружения.
3. Установка зависимостей интеграционных тестов.
4. Сборка docker-образов `backend` и `client`.
5. Запуск контейнеров `db`, `backend`, `client`.
6. Ожидание готовности backend по `/api/v1/health`.
7. Запуск интеграционных тестов `pytest`.
8. Вывод логов и остановка контейнеров.

## Интеграционные тесты

Тесты расположены в `Lab Work №5/integration_tests/test_api_integration.py`.

Проверяемые сценарии:
- доступность health endpoint;
- получение списка клиентов через `GET /customers`;
- создание клиента через `POST /customers`;
- создание заказа через `POST /orders`;
- получение заказа через `GET /orders/{id}`;
- обновление заказа через `PUT /orders/{id}`;
- смена статуса заказа через `POST /orders/{id}/status`;
- получение уведомлений через `GET /orders/{id}/notifications`;
- удаление заказа через `DELETE /orders/{id}`;
- подтверждение записи в PostgreSQL прямым SQL-запросом.

Локальный запуск интеграционных тестов:

```bash
pip install -r "Lab Work №5/integration_tests/requirements.txt"
pytest -q "Lab Work №5/integration_tests/test_api_integration.py"
```

Запуск интеграционных тестов через Docker-контейнер (без установки `pytest` на хост):

```bash
docker compose -f "Lab Work №5/docker-compose.yml" up -d db backend
docker run --rm \
  --network labwork5_sandwich-net \
  -v "$PWD/Lab Work №5/integration_tests:/tests" \
  python:3.12-slim \
  sh -lc "pip install --no-cache-dir -r /tests/requirements.txt && BASE_URL=http://sandwich-backend:8001/api/v1 POSTGRES_DSN='postgresql://sandwich:sandwich@sandwich-db:5432/sandwich?sslmode=disable' pytest -q /tests/test_api_integration.py"
docker compose -f "Lab Work №5/docker-compose.yml" down -v
```

## Непрерывное развертывание

В workflow добавлен job `publish-images`, выполняемый при push в `main`.

Публикуемые образы:
- `${DOCKERHUB_USERNAME}/sandwich-backend`
- `${DOCKERHUB_USERNAME}/sandwich-client`

Теги:
- `latest`
- `sha-<commit>`

Используемые secrets:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Публикация выполняется только при наличии указанных секретов.

## Вывод

Реализована микросервисная архитектура системы заказов с разделением на клиентский контейнер, серверный контейнер и контейнер PostgreSQL.  
Backend переведен с in-memory хранения на постоянное хранение в базе данных.  
Подготовлена контейнеризация, автоматизированная сборка и тестирование в CI, интеграционные тесты в связке с реальной БД и задел на непрерывное развертывание с публикацией образов в Docker Hub.
