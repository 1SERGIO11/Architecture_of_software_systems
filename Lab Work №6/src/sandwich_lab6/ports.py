from __future__ import annotations

from typing import Protocol

from sandwich_lab6.domain import Customer, Order


class NotificationChannel(Protocol):
    channel_name: str

    def send(self, recipient: str, message: str) -> str:
        ...


class CustomerRepository(Protocol):
    def add(self, customer: Customer) -> None:
        ...

    def get(self, customer_id: str) -> Customer | None:
        ...

    def list(self) -> list[Customer]:
        ...


class OrderRepository(Protocol):
    def save(self, order: Order) -> None:
        ...

    def get(self, order_id: str) -> Order | None:
        ...

    def list(self) -> list[Order]:
        ...

