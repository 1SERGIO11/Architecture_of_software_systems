# Исходный код лабораторной работы №3

## Запуск сервера

```bash
cd "Lab Work №3/src"
python3 -m sandwich_app.server.api
```

## Пример клиента

```bash
cd "Lab Work №3/src"
python3 -m sandwich_app.client.mobile_client
```

> Модуль клиента реализован как библиотека `MobileAppClient`; для демонстрации используйте его в Python shell или тестах.

## Запуск тестов

```bash
cd "Lab Work №3/src"
python3 -m unittest discover -s tests -v
```
