# Результаты прогонов HTTP-сценариев

Базовый URL: `http://127.0.0.1:50477`

## Шаг 1: GET /api/v1/health

Запрос:
```json
null
```

Ответ: HTTP 200
```json
{
  "status": "ok"
}
```

## Шаг 2: POST /api/v1/customers

Запрос:
```json
{
  "customer_id": "demo-c1",
  "name": "Demo",
  "email": "demo@example.com",
  "push_token": "push-demo"
}
```

Ответ: HTTP 201
```json
{
  "customer_id": "demo-c1",
  "name": "Demo",
  "email": "demo@example.com",
  "push_token": "push-demo",
  "push_enabled": true,
  "email_enabled": true
}
```

## Шаг 3: POST /api/v1/customers

Запрос:
```json
{
  "customer_id": "demo-c1",
  "name": "Demo"
}
```

Ответ: HTTP 409
```json
{
  "error": "Клиент demo-c1 уже существует."
}
```

## Шаг 4: GET /api/v1/customers/demo-c1

Запрос:
```json
null
```

Ответ: HTTP 200
```json
{
  "customer_id": "demo-c1",
  "name": "Demo",
  "email": "demo@example.com",
  "push_token": "push-demo",
  "push_enabled": true,
  "email_enabled": true
}
```

## Шаг 5: GET /api/v1/customers/missing

Запрос:
```json
null
```

Ответ: HTTP 404
```json
{
  "error": "Клиент missing не найден."
}
```

## Шаг 6: POST /api/v1/orders

Запрос:
```json
{
  "order_id": "demo-o1",
  "customer_id": "demo-c1",
  "store_id": "store-1",
  "fulfillment": "pickup",
  "total_amount": 320
}
```

Ответ: HTTP 201
```json
{
  "order_id": "demo-o1",
  "customer_id": "demo-c1",
  "store_id": "store-1",
  "fulfillment": "pickup",
  "status": "placed",
  "history": [
    "placed"
  ],
  "total_amount": 320.0,
  "updated_at": "2026-03-10T15:30:28.380218+00:00"
}
```

## Шаг 7: POST /api/v1/orders

Запрос:
```json
{
  "order_id": "demo-o2",
  "customer_id": "missing",
  "store_id": "store-1",
  "fulfillment": "pickup",
  "total_amount": 320
}
```

Ответ: HTTP 400
```json
{
  "error": "Нельзя создать заказ: клиент missing не найден."
}
```

## Шаг 8: GET /api/v1/orders

Запрос:
```json
null
```

Ответ: HTTP 200
```json
{
  "items": [
    {
      "order_id": "demo-o1",
      "customer_id": "demo-c1",
      "store_id": "store-1",
      "fulfillment": "pickup",
      "status": "placed",
      "history": [
        "placed"
      ],
      "total_amount": 320.0,
      "updated_at": "2026-03-10T15:30:28.380218+00:00"
    }
  ]
}
```

## Шаг 9: GET /api/v1/orders/demo-o1

Запрос:
```json
null
```

Ответ: HTTP 200
```json
{
  "order_id": "demo-o1",
  "customer_id": "demo-c1",
  "store_id": "store-1",
  "fulfillment": "pickup",
  "status": "placed",
  "history": [
    "placed"
  ],
  "total_amount": 320.0,
  "updated_at": "2026-03-10T15:30:28.380218+00:00"
}
```

## Шаг 10: PUT /api/v1/orders/demo-o1

Запрос:
```json
{
  "total_amount": 410
}
```

Ответ: HTTP 200
```json
{
  "order_id": "demo-o1",
  "customer_id": "demo-c1",
  "store_id": "store-1",
  "fulfillment": "pickup",
  "status": "placed",
  "history": [
    "placed"
  ],
  "total_amount": 410.0,
  "updated_at": "2026-03-10T15:30:28.380218+00:00"
}
```

## Шаг 11: POST /api/v1/orders/demo-o1/status

Запрос:
```json
{
  "status": "in_preparation"
}
```

Ответ: HTTP 200
```json
{
  "order_id": "demo-o1",
  "customer_id": "demo-c1",
  "store_id": "store-1",
  "fulfillment": "pickup",
  "status": "in_preparation",
  "history": [
    "placed",
    "in_preparation"
  ],
  "total_amount": 410.0,
  "updated_at": "2026-03-10T15:30:28.381612+00:00"
}
```

## Шаг 12: POST /api/v1/orders/demo-o1/status

Запрос:
```json
{
  "status": "delivered"
}
```

Ответ: HTTP 400
```json
{
  "error": "Нельзя перевести заказ demo-o1 из in_preparation в delivered."
}
```

## Шаг 13: GET /api/v1/orders/demo-o1/notifications

Запрос:
```json
null
```

Ответ: HTTP 200
```json
{
  "items": [
    {
      "notification_id": "4c21bc41-82f8-49a2-bf3d-ca59136592b3",
      "order_id": "demo-o1",
      "channel": "push",
      "recipient": "push-demo",
      "message": "Заказ принят: заказ #demo-o1, статус placed.",
      "created_at": "2026-03-10T15:30:28.380255+00:00"
    },
    {
      "notification_id": "5b80bc37-5d45-4432-b316-9a4adb588fa8",
      "order_id": "demo-o1",
      "channel": "email",
      "recipient": "demo@example.com",
      "message": "Заказ принят: заказ #demo-o1, статус placed.",
      "created_at": "2026-03-10T15:30:28.380265+00:00"
    },
    {
      "notification_id": "194737ca-1b0a-4bbb-89d3-b87bc16fb9e7",
      "order_id": "demo-o1",
      "channel": "push",
      "recipient": "push-demo",
      "message": "Заказ готовится: заказ #demo-o1, статус in_preparation.",
      "created_at": "2026-03-10T15:30:28.381627+00:00"
    },
    {
      "notification_id": "fa459ffe-c159-4719-a728-87cffc0c6328",
      "order_id": "demo-o1",
      "channel": "email",
      "recipient": "demo@example.com",
      "message": "Заказ готовится: заказ #demo-o1, статус in_preparation.",
      "created_at": "2026-03-10T15:30:28.381631+00:00"
    }
  ]
}
```

## Шаг 14: DELETE /api/v1/orders/demo-o1

Запрос:
```json
null
```

Ответ: HTTP 204
```json
null
```

## Шаг 15: DELETE /api/v1/orders/demo-o1

Запрос:
```json
null
```

Ответ: HTTP 404
```json
{
  "error": "Заказ demo-o1 не найден."
}
```
