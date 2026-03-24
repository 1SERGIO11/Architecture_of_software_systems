# Lab Work №5

## Структура
- Отчет: `docs/README.md`
- Оркестрация контейнеров: `docker-compose.yml`
- Backend API: `backend/`
- Web client container: `client/`
- Интеграционные тесты: `integration_tests/`
- CI/CD workflow: `../.github/workflows/lab5-ci-cd.yml`

## Сборка и запуск

```bash
docker compose -f "Lab Work №5/docker-compose.yml" build
docker compose -f "Lab Work №5/docker-compose.yml" up -d
```

Проверка доступности API и клиента:

```bash
curl http://127.0.0.1:8001/api/v1/health
open http://127.0.0.1:8080
```

Остановка сервисов:

```bash
docker compose -f "Lab Work №5/docker-compose.yml" down -v
```

## Что делает UI-клиент
- Проверка состояния API (`/health`).
- Просмотр и поиск списка клиентов.
- Создание клиента.
- Создание заказа.
- Просмотр списка заказов с фильтрами.
- Обновление заказа (`PUT`), смена статуса (`POST /status`), удаление (`DELETE`).
- Просмотр уведомлений по заказу.

## Запуск интеграционных тестов

```bash
pip install -r "Lab Work №5/integration_tests/requirements.txt"
pytest -q "Lab Work №5/integration_tests/test_api_integration.py"
```

Запуск без локальной установки `pytest` (через Docker):

```bash
docker compose -f "Lab Work №5/docker-compose.yml" up -d db backend
docker run --rm \
  --network labwork5_sandwich-net \
  -v "$PWD/Lab Work №5/integration_tests:/tests" \
  python:3.12-slim \
  sh -lc "pip install --no-cache-dir -r /tests/requirements.txt && BASE_URL=http://sandwich-backend:8001/api/v1 POSTGRES_DSN='postgresql://sandwich:sandwich@sandwich-db:5432/sandwich?sslmode=disable' pytest -q /tests/test_api_integration.py"
docker compose -f "Lab Work №5/docker-compose.yml" down -v
```

## CI/CD
- `ci` job собирает Docker-образы, поднимает `db + backend + client`, затем запускает интеграционные тесты.
- `publish-images` job публикует образы в Docker Hub при `push` в `main` и наличии `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN`.
