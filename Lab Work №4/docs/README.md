# Лабораторная работа №4

**Тема:** Проектирование REST API  
**Цель работы:** Получить опыт проектирования программного интерфейса.

## Документация по API

### Общие сведения
- Базовый URL: `http://127.0.0.1:8001/api/v1`
- Формат данных: JSON (`application/json; charset=utf-8`)
- Версия API: `v1`
- Аутентификация: не используется
- Единый формат ошибок:

```json
{
  "error": "Текст ошибки"
}
```

### Ключевые правила API
- клиент должен быть создан до оформления заказа;
- `fulfillment` может принимать только значения `pickup` или `delivery`;
- `total_amount` не может быть отрицательным;
- `updated_at` меняется при создании заказа, обновлении его параметров и смене статуса;
- уведомления создаются при создании заказа и при каждом успешном переходе в новый статус;
- допустимые переходы статусов зависят от типа исполнения заказа:
  - `pickup`: `placed -> in_preparation -> ready_for_pickup -> delivered`;
  - `delivery`: `placed -> in_preparation -> ready_for_pickup -> out_for_delivery -> delivered`.

### 1. Проверка доступности сервиса

Метод: `GET`  
URL: `/health`

Назначение: проверка работоспособности API.

Параметры запроса: отсутствуют.  
Заголовки запроса: отсутствуют.  
Тело запроса: отсутствует.

Формат ответа: JSON-объект со статусом сервиса.

Образец ответа (`200 OK`):

```json
{
  "status": "ok"
}
```

### 2. Создание клиента

Метод: `POST`  
URL: `/customers`

Назначение: создание карточки клиента для дальнейшего оформления заказов.

Параметры запроса: отсутствуют.  
Заголовки запроса:
- `Content-Type: application/json; charset=utf-8`

Тело запроса (JSON):

```json
{
  "customer_id": "c-100",
  "name": "Postman User",
  "email": "postman@example.com",
  "push_token": "push-postman",
  "push_enabled": true,
  "email_enabled": true
}
```

Формат ответа: JSON-объект с данными созданного клиента.

Образец ответа (`201 Created`):

```json
{
  "customer_id": "c-100",
  "name": "Postman User",
  "email": "postman@example.com",
  "push_token": "push-postman",
  "push_enabled": true,
  "email_enabled": true
}
```

### 3. Получение клиента

Метод: `GET`  
URL: `/customers/{customer_id}`

Назначение: получение данных конкретного клиента.

Параметры запроса:
- `customer_id` (path, обязательный)

Заголовки запроса: отсутствуют.  
Тело запроса: отсутствует.

Формат ответа: JSON-объект клиента.

Образец ответа (`200 OK`):

```json
{
  "customer_id": "c-100",
  "name": "Postman User",
  "email": "postman@example.com",
  "push_token": "push-postman",
  "push_enabled": true,
  "email_enabled": true
}
```

### 4. Создание заказа

Метод: `POST`  
URL: `/orders`

Назначение: создание нового заказа для выбранного клиента.

Ключевые ограничения:
- клиент с указанным `customer_id` должен существовать;
- `total_amount >= 0`;
- `fulfillment` должен быть равен `pickup` или `delivery`.

Параметры запроса: отсутствуют.  
Заголовки запроса:
- `Content-Type: application/json; charset=utf-8`

Тело запроса (JSON):

```json
{
  "order_id": "o-100",
  "customer_id": "c-100",
  "store_id": "store-01",
  "fulfillment": "pickup",
  "total_amount": 420.5
}
```

Формат ответа: JSON-объект заказа.

Образец ответа (`201 Created`):

```json
{
  "order_id": "o-100",
  "customer_id": "c-100",
  "store_id": "store-01",
  "fulfillment": "pickup",
  "status": "placed",
  "history": ["placed"],
  "total_amount": 420.5,
  "updated_at": "2026-03-11T00:00:00+00:00"
}
```

### 5. Получение списка заказов

Метод: `GET`  
URL: `/orders`

Назначение: получение списка заказов с возможностью фильтрации.

Параметры запроса:
- `status` (query, опционально)
- `customer_id` (query, опционально)

Значение параметра `status`, если оно передано, должно соответствовать одному из допустимых статусов заказа.

Заголовки запроса: отсутствуют.  
Тело запроса: отсутствует.

Формат ответа: JSON-объект с массивом заказов в поле `items`.

Образец ответа (`200 OK`):

```json
{
  "items": [
    {
      "order_id": "o-100",
      "customer_id": "c-100",
      "store_id": "store-01",
      "fulfillment": "pickup",
      "status": "placed",
      "history": ["placed"],
      "total_amount": 420.5,
      "updated_at": "2026-03-11T00:00:00+00:00"
    }
  ]
}
```

### 6. Получение заказа

Метод: `GET`  
URL: `/orders/{order_id}`

Назначение: получение карточки конкретного заказа.

Параметры запроса:
- `order_id` (path, обязательный)

Заголовки запроса: отсутствуют.  
Тело запроса: отсутствует.

Формат ответа: JSON-объект заказа.

Образец ответа (`200 OK`):

```json
{
  "order_id": "o-100",
  "customer_id": "c-100",
  "store_id": "store-01",
  "fulfillment": "pickup",
  "status": "placed",
  "history": ["placed"],
  "total_amount": 420.5,
  "updated_at": "2026-03-11T00:00:00+00:00"
}
```

### 7. Изменение статуса заказа

Метод: `POST`  
URL: `/orders/{order_id}/status`

Назначение: перевод заказа в следующий допустимый статус.

Переход будет принят только в том случае, если он разрешен для текущего типа заказа (`pickup` или `delivery`).

Параметры запроса:
- `order_id` (path, обязательный)

Заголовки запроса:
- `Content-Type: application/json; charset=utf-8`

Тело запроса (JSON):

```json
{
  "status": "in_preparation"
}
```

Формат ответа: JSON-объект заказа с обновленным статусом и историей.

Образец ответа (`200 OK`):

```json
{
  "order_id": "o-100",
  "customer_id": "c-100",
  "store_id": "store-01",
  "fulfillment": "pickup",
  "status": "in_preparation",
  "history": ["placed", "in_preparation"],
  "total_amount": 499.9,
  "updated_at": "2026-03-11T00:05:00+00:00"
}
```

### 8. Получение уведомлений по заказу

Метод: `GET`  
URL: `/orders/{order_id}/notifications`

Назначение: получение списка сформированных уведомлений для заказа.

В список попадают уведомления, созданные в момент оформления заказа и после каждой успешной смены статуса.

Параметры запроса:
- `order_id` (path, обязательный)

Заголовки запроса: отсутствуют.  
Тело запроса: отсутствует.

Формат ответа: JSON-объект с массивом уведомлений в поле `items`.

Образец ответа (`200 OK`):

```json
{
  "items": [
    {
      "notification_id": "1f8e6f0b-0e52-4dd6-90cb-8a8ee4564db2",
      "order_id": "o-100",
      "channel": "push",
      "recipient": "push-postman",
      "message": "Заказ готовится: заказ #o-100, статус in_preparation.",
      "created_at": "2026-03-11T00:05:01+00:00"
    }
  ]
}
```

### 9. Обновление параметров заказа

Метод: `PUT`  
URL: `/orders/{order_id}`

Назначение: обновление параметров существующего заказа.

Допускается изменение `store_id`, `fulfillment` и `total_amount`. После успешного обновления поле `updated_at` должно содержать новое время изменения.

Параметры запроса:
- `order_id` (path, обязательный)

Заголовки запроса:
- `Content-Type: application/json; charset=utf-8`

Тело запроса (JSON):

```json
{
  "total_amount": 499.9,
  "store_id": "store-02",
  "fulfillment": "pickup"
}
```

Формат ответа: JSON-объект обновленного заказа.

Образец ответа (`200 OK`):

```json
{
  "order_id": "o-100",
  "customer_id": "c-100",
  "store_id": "store-02",
  "fulfillment": "pickup",
  "status": "placed",
  "history": ["placed"],
  "total_amount": 499.9,
  "updated_at": "2026-03-11T00:03:00+00:00"
}
```

### 10. Удаление заказа

Метод: `DELETE`  
URL: `/orders/{order_id}`

Назначение: удаление заказа по идентификатору.

Параметры запроса:
- `order_id` (path, обязательный)

Заголовки запроса: отсутствуют.  
Тело запроса: отсутствует.

Формат ответа:
- успешный ответ: `204 No Content` (тело отсутствует);
- при ошибке: JSON-объект ошибки.

Образец ответа при ошибке (`404 Not Found`):

```json
{
  "error": "Заказ o-100 не найден."
}
```

## Тестирование API

### Использованные артефакты
- Postman collection: `docs/postman/LabWork4.postman_collection.json`
- Postman environment: `docs/postman/LabWork4.local.postman_environment.json`
- Сводный прогон HTTP-сценариев: `docs/postman/run_results.json`, `docs/postman/run_results.md`
- Скриншоты Postman: `docs/img/postman/`

### Что проверено
- коллекция Postman покрывает базовый CRUD-сценарий и ключевые ошибки API;
- автотесты `src/tests/test_api.py` дополнительно проверяют валидацию отрицательной суммы и недопустимого `fulfillment`;
- доступность сервиса;
- создание и получение клиента;
- защита от дублирования клиента;
- создание заказа и запрет создания заказа для неизвестного клиента;
- фильтрация и получение заказов;
- обновление параметров заказа;
- смена статуса с проверкой допустимых переходов;
- формирование и чтение уведомлений;
- удаление заказа и корректная обработка повторного удаления;
- ошибки валидации для отрицательной суммы и недопустимого `fulfillment`.

### Артефакты Postman

#### 1. `GET /health`

<p>
  <img src="img/postman/01_health_request.png" alt="01 health request" width="32%">
  <img src="img/postman/01_health_response.png" alt="01 health response" width="32%">
  <img src="img/postman/01_health_tests.png" alt="01 health tests" width="32%">
</p>

#### 2. `POST /customers`

<p>
  <img src="img/postman/02_create_customer_request.png" alt="02 create customer request" width="32%">
  <img src="img/postman/02_create_customer_response.png" alt="02 create customer response" width="32%">
  <img src="img/postman/02_create_customer_tests.png" alt="02 create customer tests" width="32%">
</p>

#### 3. `GET /customers/{id}`

<p>
  <img src="img/postman/03_get_customer_request.png" alt="03 get customer request" width="32%">
  <img src="img/postman/03_get_customer_response.png" alt="03 get customer response" width="32%">
  <img src="img/postman/03_get_customer_tests.png" alt="03 get customer tests" width="32%">
</p>

#### 4. `POST /orders`

<p>
  <img src="img/postman/04_create_order_request.png" alt="04 create order request" width="32%">
  <img src="img/postman/04_create_order_response.png" alt="04 create order response" width="32%">
  <img src="img/postman/04_create_order_tests.png" alt="04 create order tests" width="32%">
</p>

#### 5. `GET /orders`

<p>
  <img src="img/postman/05_list_orders_request.png" alt="05 list orders request" width="32%">
  <img src="img/postman/05_list_orders_response.png" alt="05 list orders response" width="32%">
  <img src="img/postman/05_list_orders_tests.png" alt="05 list orders tests" width="32%">
</p>

#### 6. `GET /orders/{id}`

<p>
  <img src="img/postman/06_get_order_request.png" alt="06 get order request" width="32%">
  <img src="img/postman/06_get_order_response.png" alt="06 get order response" width="32%">
  <img src="img/postman/06_get_order_tests.png" alt="06 get order tests" width="32%">
</p>

#### 7. `POST /orders/{id}/status`

<p>
  <img src="img/postman/07_change_status_request.png" alt="07 change status request" width="32%">
  <img src="img/postman/07_change_status_response.png" alt="07 change status response" width="32%">
  <img src="img/postman/07_change_status_tests.png" alt="07 change status tests" width="32%">
</p>

#### 8. `GET /orders/{id}/notifications`

<p>
  <img src="img/postman/08_get_notifications_request.png" alt="08 get notifications request" width="32%">
  <img src="img/postman/08_get_notifications_response.png" alt="08 get notifications response" width="32%">
  <img src="img/postman/08_get_notifications_tests.png" alt="08 get notifications tests" width="32%">
</p>

#### 9. `PUT /orders/{id}`

<p>
  <img src="img/postman/09_update_order_request.png" alt="09 update order request" width="32%">
  <img src="img/postman/09_update_order_response.png" alt="09 update order response" width="32%">
  <img src="img/postman/09_update_order_tests.png" alt="09 update order tests" width="32%">
</p>

#### 10. `DELETE /orders/{id}`

<p>
  <img src="img/postman/10_delete_order_request.png" alt="10 delete order request" width="32%">
  <img src="img/postman/10_delete_order_response.png" alt="10 delete order response" width="32%">
  <img src="img/postman/10_delete_order_tests.png" alt="10 delete order tests" width="32%">
</p>

### Код автотестов в Postman

Образец автотеста статуса ответа:

```javascript
pm.test('Status 200', function () {
  pm.response.to.have.status(200);
});
```

Образец проверки содержимого ответа:

```javascript
const data = pm.response.json();
pm.test('Response contains status field', function () {
  pm.expect(data).to.have.property('status');
});
```

Полный набор автотестов находится в `docs/postman/LabWork4.postman_collection.json`.

## Запуск API и тестов

Запуск сервера:

```bash
cd "Lab Work №4/src"
python3 -m order_api.api
```

Запуск интеграционных тестов:

```bash
cd "Lab Work №4/src"
python3 -m unittest discover -s tests -v
```

## Вывод

Выполнено проектирование и реализация REST API сервиса заказов с методами `GET`, `POST`, `PUT`, `DELETE`.  
Подготовлена полная документация endpoint'ов с единым форматом описания запросов и ответов, а также оформлены результаты тестирования в Postman и автоматические проверки API.
