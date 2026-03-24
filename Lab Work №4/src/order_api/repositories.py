from __future__ import annotations

from typing import Protocol

from order_api.models import Customer, NotificationRecord, Order


class CustomerRepository(Protocol):
    def add(self, customer: Customer) -> None: ...

    def get(self, customer_id: str) -> Customer | None: ...


class OrderRepository(Protocol):
    def add(self, order: Order) -> None: ...

    def get(self, order_id: str) -> Order | None: ...

    def save(self, order: Order) -> None: ...

    def delete(self, order_id: str) -> bool: ...

    def list(self) -> list[Order]: ...


class NotificationRepository(Protocol):
    def add(self, notification: NotificationRecord) -> None: ...

    def list_by_order(self, order_id: str) -> list[NotificationRecord]: ...


class InMemoryCustomerRepository(CustomerRepository):
    def __init__(self) -> None:
        self._storage: dict[str, Customer] = {}

    def add(self, customer: Customer) -> None:
        self._storage[customer.customer_id] = customer

    def get(self, customer_id: str) -> Customer | None:
        return self._storage.get(customer_id)


class InMemoryOrderRepository(OrderRepository):
    def __init__(self) -> None:
        self._storage: dict[str, Order] = {}

    def add(self, order: Order) -> None:
        self._storage[order.order_id] = order

    def get(self, order_id: str) -> Order | None:
        return self._storage.get(order_id)

    def save(self, order: Order) -> None:
        self._storage[order.order_id] = order

    def delete(self, order_id: str) -> bool:
        return self._storage.pop(order_id, None) is not None

    def list(self) -> list[Order]:
        return list(self._storage.values())


class InMemoryNotificationRepository(NotificationRepository):
    def __init__(self) -> None:
        self._storage: list[NotificationRecord] = []

    def add(self, notification: NotificationRecord) -> None:
        self._storage.append(notification)

    def list_by_order(self, order_id: str) -> list[NotificationRecord]:
        return [item for item in self._storage if item.order_id == order_id]
