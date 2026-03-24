from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sandwich_app.server.domain.models import Order, OrderStatus


@dataclass(frozen=True)
class OutboundNotification:
    order_id: str
    status: OrderStatus
    channel: str
    recipient: str
    message: str


class OrderRepository(Protocol):
    def add(self, order: Order) -> None: ...

    def get(self, order_id: str) -> Order | None: ...

    def save(self, order: Order) -> None: ...


class NotificationDispatcher(Protocol):
    def dispatch_status_changed(self, order: Order) -> list[OutboundNotification]: ...
