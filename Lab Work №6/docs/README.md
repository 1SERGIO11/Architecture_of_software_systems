# Лабораторная работа №6

**Тема:** Использование шаблонов проектирования  
**Цель работы:** Получить опыт применения шаблонов проектирования при написании кода программной системы.

## Контекст реализуемой системы

В качестве основы использована предметная область предыдущих лабораторных работ: система управления заказами и уведомлениями `sandwich app`.  
Для ЛР6 реализован отдельный модуль `src/sandwich_lab6`, в котором жизненный цикл заказа (создание, расчет суммы, смена статуса, уведомления) организован через GoF-паттерны и проанализирован через GRASP.

## Шаблоны проектирования GoF

## Порождающие шаблоны

### 1) Singleton — `AppConfig`

- Общее назначение: гарантировать единственный экземпляр объекта конфигурации.
- Назначение в проекте: единый источник параметров расчета (`delivery_fee`, `currency`) для всех сценариев создания заказа.

UML:

![UML Diagram](img/gof_singleton.svg)

Фрагмент кода:

```python
class AppConfig:
    _instance: AppConfig | None = None

    def __new__(cls) -> AppConfig:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.delivery_fee = 89.0
        return cls._instance
```

### 2) Builder — `OrderBuilder`

- Общее назначение: пошаговая сборка сложного объекта.
- Назначение в проекте: безопасное создание `Order` с цепочкой методов (`with_order_id`, `with_customer_id`, `with_amount`, ...), без перегруженного конструктора.

UML:

![UML Diagram](img/gof_builder.svg)

Фрагмент кода:

```python
order = (
    OrderBuilder()
    .with_order_id("o-601")
    .with_customer_id("c-100")
    .with_store_id("store-1")
    .with_fulfillment(FulfillmentType.PICKUP)
    .with_amount(500.0)
    .build()
)
```

### 3) Factory Method — `NotificationChannelCreator`

- Общее назначение: делегировать создание объектов подклассам.
- Назначение в проекте: независимое создание разных каналов уведомлений (`push`, `email`) без изменения бизнес-логики.

UML:

![UML Diagram](img/gof_factory_method.svg)

Фрагмент кода:

```python
class EmailChannelCreator(NotificationChannelCreator):
    def create_channel(self) -> NotificationChannel:
        return EmailGatewayAdapter(LegacyEmailGateway())
```

## Структурные шаблоны

### 4) Adapter — `EmailGatewayAdapter`, `PushGatewayAdapter`

- Общее назначение: привести несовместимые интерфейсы к целевому контракту.
- Назначение в проекте: интеграция legacy SDK с единым интерфейсом `NotificationChannel.send(recipient, message)`.

UML:

![UML Diagram](img/gof_adapter.svg)

Фрагмент кода:

```python
class PushGatewayAdapter:
    channel_name = "push"

    def send(self, recipient: str, message: str) -> str:
        return self._gateway.push(token=recipient, title="Sandwich App", message=message)
```

### 5) Decorator — `AuditNotificationDecorator`

- Общее назначение: динамически расширять поведение объекта без изменения класса.
- Назначение в проекте: журналирование вызовов отправки уведомлений до и после реальной отправки.

UML:

![UML Diagram](img/gof_decorator.svg)

Фрагмент кода:

```python
class AuditNotificationDecorator(NotificationChannelDecorator):
    def send(self, recipient: str, message: str) -> str:
        self._audit_log.append(f"before:{self.channel_name}:{recipient}")
        result = super().send(recipient, message)
        self._audit_log.append(f"after:{self.channel_name}:{recipient}")
        return result
```

### 6) Proxy — `CustomerRepositoryCacheProxy`

- Общее назначение: контролировать доступ к целевому объекту.
- Назначение в проекте: кэширование обращений к репозиторию клиентов и сбор метрики `cache_hits`.

UML:

![UML Diagram](img/gof_proxy.svg)

Фрагмент кода:

```python
def get(self, customer_id: str) -> Customer | None:
    if customer_id in self._cache:
        self.cache_hits += 1
        return self._cache[customer_id]
    customer = self._origin.get(customer_id)
```

### 7) Facade — `OrderManagementFacade`

- Общее назначение: предоставить единый упрощенный интерфейс к набору подсистем.
- Назначение в проекте: одна точка входа для операций `create_order`, `change_order_status`, `list_customers`, `list_orders`.

UML:

![UML Diagram](img/gof_facade.svg)

Фрагмент кода:

```python
def create_order(self, builder: OrderBuilder) -> Order:
    order = builder.build()
    validation = CustomerExistsValidator(self._customer_repo)
    validation.set_next(PositiveAmountValidator())
    validation.handle(ValidationContext(order=order))
    order.final_amount = self._pricing[order.fulfillment].calculate(order.base_amount)
    self._order_repo.save(order)
```

## Поведенческие шаблоны

### 8) Strategy — `PricingStrategy`

- Общее назначение: инкапсулировать взаимозаменяемые алгоритмы.
- Назначение в проекте: выбор алгоритма расчета итоговой суммы по типу получения (`pickup`, `delivery`).

UML:

![UML Diagram](img/gof_strategy.svg)

Фрагмент кода:

```python
self._pricing = {
    FulfillmentType.PICKUP: PickupPricingStrategy(),
    FulfillmentType.DELIVERY: DeliveryPricingStrategy(config.delivery_fee),
}
```

### 9) Observer — `OrderEventPublisher`, `NotificationObserver`

- Общее назначение: оповещать подписчиков об изменении состояния издателя.
- Назначение в проекте: реакция подсистемы уведомлений на события заказа (`создан`, `изменен статус`).

UML:

![UML Diagram](img/gof_observer.svg)

Фрагмент кода:

```python
publisher.subscribe(observer)
publisher.publish(OrderEvent(...))
```

### 10) State — `OrderStateMachine` + состояния

- Общее назначение: изменять поведение объекта в зависимости от текущего состояния.
- Назначение в проекте: управление допустимыми переходами статусов заказа с учетом `pickup/delivery`.

UML:

![UML Diagram](img/gof_state.svg)

Фрагмент кода:

```python
def transition(self, order: Order, target: OrderStatus) -> None:
    if not self.can_transition(order, target):
        raise ValueError(...)
    order.set_status(target)
```

### 11) Command — `CreateOrderCommand`, `ChangeStatusCommand`, `CommandBus`

- Общее назначение: инкапсулировать запрос как объект.
- Назначение в проекте: унифицированный запуск бизнес-операций и возможность журналирования/расширения через `CommandBus`.

UML:

![UML Diagram](img/gof_command.svg)

Фрагмент кода:

```python
created = bus.execute(CreateOrderCommand(facade, builder))
updated = bus.execute(ChangeStatusCommand(facade, "o-603", OrderStatus.IN_PREPARATION))
```

### 12) Chain of Responsibility — валидация заказа

- Общее назначение: передавать запрос по цепочке обработчиков.
- Назначение в проекте: независимые проверки при создании/изменении заказа (`CustomerExistsValidator`, `PositiveAmountValidator`, `StatusTransitionValidator`).

UML:

![UML Diagram](img/gof_chain.svg)

Фрагмент кода:

```python
validation = CustomerExistsValidator(self._customer_repo)
validation.set_next(PositiveAmountValidator())
validation.handle(ValidationContext(order=order))
```

## Шаблоны проектирования GRASP

## Роли (обязанности) классов

### 1) Information Expert

- Проблема: кто должен знать корректные переходы статусов заказа.
- Решение: `OrderStateMachine` и состояния (`PlacedState`, `ReadyForPickupState`, ...) содержат правила переходов.
- Пример кода:

```python
if not self.can_transition(order, target):
    raise ValueError(...)
```

- Результат: правила сосредоточены в одном месте, а не размазаны по сервисам.
- Связь с паттернами: State, Chain of Responsibility.

### 2) Creator

- Проблема: кто должен создавать объект `Order`.
- Решение: `OrderBuilder` отвечает за конструирование заказа.
- Пример кода:

```python
OrderBuilder().with_order_id(...).with_customer_id(...).build()
```

- Результат: создание объекта стало контролируемым и читаемым.
- Связь с паттернами: Builder.

### 3) Controller

- Проблема: какой объект принимает системные команды сценария.
- Решение: `OrderManagementFacade` выступает контроллером прикладного слоя.
- Пример кода:

```python
facade.create_order(builder)
facade.change_order_status(order_id, status)
```

- Результат: единая точка входа в use-case, прозрачная оркестрация.
- Связь с паттернами: Facade, Command.

### 4) Polymorphism

- Проблема: как убрать `if/else`-ветвления для вариантов поведения.
- Решение: разные реализации `PricingStrategy` и `OrderState`.
- Пример кода:

```python
order.final_amount = self._pricing[order.fulfillment].calculate(order.base_amount)
```

- Результат: расширяемость без переписывания существующего кода.
- Связь с паттернами: Strategy, State.

### 5) Pure Fabrication

- Проблема: доменные сущности не должны зависеть от инфраструктурных SDK.
- Решение: адаптеры и наблюдатели выделены в отдельные сервисные классы (`EmailGatewayAdapter`, `NotificationObserver`).
- Пример кода:

```python
channel = creator.create_audited_channel(self._audit_log)
channel.send(recipient, event.text)
```

- Результат: доменная модель остается чистой.
- Связь с паттернами: Adapter, Observer, Factory Method.

## Принципы разработки

### 1) Low Coupling

- Проблема: сильные зависимости между слоями усложняют изменения.
- Решение: использование абстракций `CustomerRepository`, `OrderRepository`, `NotificationChannel`.
- Пример кода:

```python
def __init__(self, customer_repo: CustomerRepository, order_repo: OrderRepository, ...):
    ...
```

- Результат: можно менять реализации хранилища и каналов независимо.
- Связь с паттернами: Proxy, Adapter, Facade.

### 2) High Cohesion

- Проблема: смешение обязанностей внутри одного класса.
- Решение: отдельные классы для валидации, расчета, смены статусов, отправки уведомлений.
- Пример кода:

```python
class StatusTransitionValidator(ValidationHandler):
    ...
```

- Результат: классы короткие, целевые и проще в тестировании.
- Связь с паттернами: Chain of Responsibility, Strategy, State.

### 3) Protected Variations

- Проблема: внешние изменения (новый канал/новая стратегия) не должны ломать ядро.
- Решение: точки расширения вынесены в полиморфные интерфейсы.
- Пример кода:

```python
class NotificationChannelCreator(ABC):
    @abstractmethod
    def create_channel(self) -> NotificationChannel:
        ...
```

- Результат: добавление нового канала не требует изменения `OrderManagementFacade`.
- Связь с паттернами: Factory Method, Strategy, Observer.

## Свойство программы (цель)

### Расширяемость

- Проблема: система должна развиваться без каскадного рефакторинга.
- Решение: комбинация GoF-паттернов с GRASP-принципами (Facade + Strategy + Factory Method + Observer + Low Coupling).
- Пример кода:

```python
observer = NotificationObserver(customer_repo, [PushChannelCreator(), EmailChannelCreator()], audit_log)
publisher.subscribe(observer)
```

- Результат: можно добавить новый канал, новый алгоритм цены, новый обработчик валидации или новую команду локально.
- Связь с другими паттернами: Strategy, Factory Method, Observer, Command, Chain of Responsibility.

## Проверка работоспособности

Запуск демонстрационного сценария:

```bash
cd "Lab Work №6"
PYTHONPATH=src python3 -m sandwich_lab6.demo
```

Запуск тестов:

```bash
cd "Lab Work №6"
python3 -m unittest discover -s tests -v
```

Покрываемые тестами сценарии:
- singleton-конфигурация;
- список клиентов и proxy-кэш;
- создание заказа через command + builder + strategy;
- смена статуса через state machine;
- блокировка недопустимого перехода через chain of responsibility;
- аудит уведомлений через decorator.

## Вывод

В модуле `sandwich_lab6` реализован полноценный набор GoF-паттернов для предметной области системы заказов: 3 порождающих, 4 структурных и 5 поведенческих.  
Архитектура дополнительно проанализирована с позиции GRASP: выделены 5 ролей классов, 3 принципа разработки и целевое свойство программы — расширяемость.  
Полученная реализация подтверждена демонстрационным запуском и автотестами.
