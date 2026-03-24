from __future__ import annotations

from dataclasses import dataclass, field

from sandwich_lab6.domain import Customer, Order
from sandwich_lab6.ports import CustomerRepository, NotificationChannel, OrderRepository


class LegacyEmailGateway:
    """Old API with incompatible method signature."""

    def send_email(self, *, to: str, subject: str, body: str) -> str:
        return f"legacy-email:{to}:{subject}:{body}"


class LegacyPushGateway:
    """Old API with incompatible method signature."""

    def push(self, *, token: str, title: str, message: str) -> str:
        return f"legacy-push:{token}:{title}:{message}"


class EmailGatewayAdapter:
    """Adapter for legacy email API to NotificationChannel interface."""

    channel_name = "email"

    def __init__(self, gateway: LegacyEmailGateway) -> None:
        self._gateway = gateway

    def send(self, recipient: str, message: str) -> str:
        return self._gateway.send_email(to=recipient, subject="Статус заказа", body=message)


class PushGatewayAdapter:
    """Adapter for legacy push API to NotificationChannel interface."""

    channel_name = "push"

    def __init__(self, gateway: LegacyPushGateway) -> None:
        self._gateway = gateway

    def send(self, recipient: str, message: str) -> str:
        return self._gateway.push(token=recipient, title="Sandwich App", message=message)


class NotificationChannelDecorator:
    """Decorator base for notification channels."""

    def __init__(self, wrapped: NotificationChannel) -> None:
        self._wrapped = wrapped

    @property
    def channel_name(self) -> str:
        return self._wrapped.channel_name

    def send(self, recipient: str, message: str) -> str:
        return self._wrapped.send(recipient, message)


class AuditNotificationDecorator(NotificationChannelDecorator):
    """Decorator adds audit logs around channel send operation."""

    def __init__(self, wrapped: NotificationChannel, audit_log: list[str]) -> None:
        super().__init__(wrapped)
        self._audit_log = audit_log

    def send(self, recipient: str, message: str) -> str:
        self._audit_log.append(f"before:{self.channel_name}:{recipient}")
        result = super().send(recipient, message)
        self._audit_log.append(f"after:{self.channel_name}:{recipient}")
        return result


@dataclass
class InMemoryCustomerRepository(CustomerRepository):
    _storage: dict[str, Customer] = field(default_factory=dict)

    def add(self, customer: Customer) -> None:
        self._storage[customer.customer_id] = customer

    def get(self, customer_id: str) -> Customer | None:
        return self._storage.get(customer_id)

    def list(self) -> list[Customer]:
        return [self._storage[key] for key in sorted(self._storage)]


@dataclass
class CustomerRepositoryCacheProxy(CustomerRepository):
    """Proxy adds cache and hit metrics for customer access."""

    _origin: CustomerRepository
    _cache: dict[str, Customer] = field(default_factory=dict)
    cache_hits: int = 0

    def add(self, customer: Customer) -> None:
        self._origin.add(customer)
        self._cache[customer.customer_id] = customer

    def get(self, customer_id: str) -> Customer | None:
        if customer_id in self._cache:
            self.cache_hits += 1
            return self._cache[customer_id]
        customer = self._origin.get(customer_id)
        if customer:
            self._cache[customer_id] = customer
        return customer

    def list(self) -> list[Customer]:
        items = self._origin.list()
        for item in items:
            self._cache[item.customer_id] = item
        return items


@dataclass
class InMemoryOrderRepository(OrderRepository):
    _storage: dict[str, Order] = field(default_factory=dict)

    def save(self, order: Order) -> None:
        self._storage[order.order_id] = order

    def get(self, order_id: str) -> Order | None:
        return self._storage.get(order_id)

    def list(self) -> list[Order]:
        return [self._storage[key] for key in sorted(self._storage)]

