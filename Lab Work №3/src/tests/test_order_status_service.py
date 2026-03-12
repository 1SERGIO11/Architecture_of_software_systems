from __future__ import annotations

import unittest

from sandwich_app.server.domain.models import (
    CustomerContact,
    FulfillmentType,
    NotificationPreference,
    Order,
    OrderStatus,
)
from sandwich_app.server.domain.rules import InvalidTransitionError
from sandwich_app.server.ports import OutboundNotification
from sandwich_app.server.repositories.in_memory import InMemoryOrderRepository
from sandwich_app.server.services.order_status_service import (
    OrderAlreadyExistsError,
    OrderStatusService,
)


class FakeDispatcher:
    def __init__(self) -> None:
        self.sent: list[OutboundNotification] = []

    def dispatch_status_changed(self, order: Order) -> list[OutboundNotification]:
        item = OutboundNotification(
            order_id=order.order_id,
            status=order.status,
            channel="fake",
            recipient="test",
            message=f"status={order.status.value}",
        )
        self.sent.append(item)
        return [item]


class OrderStatusServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dispatcher = FakeDispatcher()
        self.repo = InMemoryOrderRepository()
        self.service = OrderStatusService(self.repo, self.dispatcher)

    def test_pickup_flow(self) -> None:
        order = self._build_order(order_id="o-1", fulfillment=FulfillmentType.PICKUP)
        self.service.create_order(order)

        result_1 = self.service.update_status("o-1", OrderStatus.IN_PREPARATION)
        result_2 = self.service.update_status("o-1", OrderStatus.READY_FOR_PICKUP)
        result_3 = self.service.update_status("o-1", OrderStatus.DELIVERED)

        self.assertEqual(result_3.order.status, OrderStatus.DELIVERED)
        self.assertEqual(
            [state.value for state in result_3.order.history],
            [
                OrderStatus.PLACED.value,
                OrderStatus.IN_PREPARATION.value,
                OrderStatus.READY_FOR_PICKUP.value,
                OrderStatus.DELIVERED.value,
            ],
        )
        self.assertEqual(len(self.dispatcher.sent), 4)
        self.assertEqual(result_1.notifications[0].status, OrderStatus.IN_PREPARATION)
        self.assertEqual(result_2.notifications[0].status, OrderStatus.READY_FOR_PICKUP)

    def test_delivery_flow(self) -> None:
        order = self._build_order(order_id="o-2", fulfillment=FulfillmentType.DELIVERY)
        self.service.create_order(order)

        self.service.update_status("o-2", OrderStatus.IN_PREPARATION)
        self.service.update_status("o-2", OrderStatus.READY_FOR_PICKUP)
        self.service.update_status("o-2", OrderStatus.OUT_FOR_DELIVERY)
        result = self.service.update_status("o-2", OrderStatus.DELIVERED)

        self.assertEqual(result.order.status, OrderStatus.DELIVERED)

    def test_invalid_transition_raises(self) -> None:
        order = self._build_order(order_id="o-3", fulfillment=FulfillmentType.PICKUP)
        self.service.create_order(order)

        with self.assertRaises(InvalidTransitionError):
            self.service.update_status("o-3", OrderStatus.OUT_FOR_DELIVERY)

    def test_duplicate_order_raises(self) -> None:
        order = self._build_order(order_id="o-4", fulfillment=FulfillmentType.PICKUP)
        self.service.create_order(order)

        with self.assertRaises(OrderAlreadyExistsError):
            self.service.create_order(order)

    @staticmethod
    def _build_order(order_id: str, fulfillment: FulfillmentType) -> Order:
        return Order(
            order_id=order_id,
            store_id="store-1",
            fulfillment=fulfillment,
            total_amount=399.0,
            customer=CustomerContact(
                customer_id="c-1",
                name="Alice",
                email="alice@example.com",
                push_token="push-token",
                preference=NotificationPreference(push_enabled=True, email_enabled=True),
            ),
        )


if __name__ == "__main__":
    unittest.main()
