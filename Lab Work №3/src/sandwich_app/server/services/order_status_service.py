from __future__ import annotations

from dataclasses import dataclass

from sandwich_app.server.domain.models import Order, OrderStatus
from sandwich_app.server.domain.rules import ensure_transition_allowed
from sandwich_app.server.ports import NotificationDispatcher, OrderRepository, OutboundNotification


class OrderNotFoundError(LookupError):
    pass


class OrderAlreadyExistsError(ValueError):
    pass


@dataclass
class StatusUpdateResult:
    order: Order
    notifications: list[OutboundNotification]


class OrderStatusService:
    def __init__(self, orders: OrderRepository, notifier: NotificationDispatcher) -> None:
        self._orders = orders
        self._notifier = notifier

    def create_order(self, order: Order) -> Order:
        existing = self._orders.get(order.order_id)
        if existing is not None:
            raise OrderAlreadyExistsError(f"Заказ {order.order_id} уже существует.")

        self._orders.add(order)
        self._notifier.dispatch_status_changed(order)
        return order

    def get_order(self, order_id: str) -> Order:
        order = self._orders.get(order_id)
        if order is None:
            raise OrderNotFoundError(f"Заказ {order_id} не найден.")
        return order

    def update_status(self, order_id: str, new_status: OrderStatus) -> StatusUpdateResult:
        order = self.get_order(order_id)
        ensure_transition_allowed(order, new_status)

        order.advance_to(new_status)
        self._orders.save(order)
        notifications = self._notifier.dispatch_status_changed(order)

        return StatusUpdateResult(order=order, notifications=notifications)
