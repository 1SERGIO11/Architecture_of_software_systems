# Результаты прогонов HTTP-сценариев

Базовый URL: `http://127.0.0.1:64185`

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
  "updated_at": "2026-03-17T14:16:32.758961+00:00"
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

## Шаг 8: POST /api/v1/orders

Запрос:
```json
{
  "order_id": "demo-o3",
  "customer_id": "demo-c1",
  "store_id": "store-1",
  "fulfillment": "pickup",
  "total_amount": -5
}
```

Ответ: HTTP 400
```json
{
  "error": "Сумма заказа не может быть отрицательной."
}
```

## Шаг 9: GET /api/v1/orders

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
      "updated_at": "2026-03-17T14:16:32.758961+00:00"
    }
  ]
}
```

## Шаг 10: GET /api/v1/orders/demo-o1

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
  "updated_at": "2026-03-17T14:16:32.758961+00:00"
}
```

## Шаг 11: PUT /api/v1/orders/demo-o1

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
  "updated_at": "2026-03-17T14:16:32.760744+00:00"
}
```

## Шаг 12: PUT /api/v1/orders/demo-o1

Запрос:
```json
{
  "fulfillment": "drone"
}
```

Ответ: HTTP 400
```json
{
  "error": "Поле fulfillment должно быть pickup или delivery."
}
```

## Шаг 13: POST /api/v1/orders/demo-o1/status

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
  "updated_at": "2026-03-17T14:16:32.761490+00:00"
}
```

## Шаг 14: POST /api/v1/orders/demo-o1/status

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

## Шаг 15: GET /api/v1/orders/demo-o1/notifications

Запрос:
```json
null
```

Ответ: HTTP 200
```json
{
  "items": [
    {
      "notification_id": "00fa8dd1-1984-4364-8234-2e1cbb5f4795",
      "order_id": "demo-o1",
      "channel": "push",
      "recipient": "push-demo",
      "message": "Заказ принят: заказ #demo-o1, статус placed.",
      "created_at": "2026-03-17T14:16:32.758986+00:00"
    },
    {
      "notification_id": "2465e2bb-20c2-49e9-8e9a-a537bfec800d",
      "order_id": "demo-o1",
      "channel": "email",
      "recipient": "demo@example.com",
      "message": "Заказ принят: заказ #demo-o1, статус placed.",
      "created_at": "2026-03-17T14:16:32.758994+00:00"
    },
    {
      "notification_id": "4340d0b2-9915-4a24-8872-7f3827f8b012",
      "order_id": "demo-o1",
      "channel": "push",
      "recipient": "push-demo",
      "message": "Заказ готовится: заказ #demo-o1, статус in_preparation.",
      "created_at": "2026-03-17T14:16:32.761510+00:00"
    },
    {
      "notification_id": "d9e2a1dd-1970-46cb-aab4-13cb79ae6755",
      "order_id": "demo-o1",
      "channel": "email",
      "recipient": "demo@example.com",
      "message": "Заказ готовится: заказ #demo-o1, статус in_preparation.",
      "created_at": "2026-03-17T14:16:32.761516+00:00"
    }
  ]
}
```

## Шаг 16: DELETE /api/v1/orders/demo-o1

Запрос:
```json
null
```

Ответ: HTTP 204
```json
null
```

## Шаг 17: DELETE /api/v1/orders/demo-o1

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
