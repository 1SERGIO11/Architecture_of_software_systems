from __future__ import annotations

import pathlib
import sys
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sandwich_lab6.behavioral import ChangeStatusCommand, CreateOrderCommand
from sandwich_lab6.bootstrap import build_context
from sandwich_lab6.creational import AppConfig, OrderBuilder
from sandwich_lab6.domain import FulfillmentType, OrderStatus
from sandwich_lab6.structural import CustomerRepositoryCacheProxy


class Lab6PatternsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.context, self.bus = build_context()
        self.facade = self.context.facade

    def test_singleton_app_config(self) -> None:
        first = AppConfig()
        second = AppConfig()
        self.assertIs(first, second)
        self.assertEqual(first.delivery_fee, 89.0)

    def test_list_customers_and_proxy_cache(self) -> None:
        customers = self.facade.list_customers()
        self.assertGreaterEqual(len(customers), 2)

        proxy = self.facade._customer_repo  # type: ignore[attr-defined]
        self.assertIsInstance(proxy, CustomerRepositoryCacheProxy)
        _ = proxy.get("c-100")
        _ = proxy.get("c-100")
        self.assertGreaterEqual(proxy.cache_hits, 1)

    def test_create_pickup_order_with_command_strategy_observer(self) -> None:
        created = self.bus.execute(
            CreateOrderCommand(
                self.facade,
                OrderBuilder()
                .with_order_id("o-601")
                .with_customer_id("c-100")
                .with_store_id("store-1")
                .with_fulfillment(FulfillmentType.PICKUP)
                .with_amount(500.0),
            )
        )
        self.assertEqual(created.final_amount, 500.0)
        self.assertEqual(created.status, OrderStatus.PLACED)
        self.assertEqual(len(self.context.observer.sent), 2)  # push + email

    def test_delivery_order_uses_delivery_strategy(self) -> None:
        created = self.bus.execute(
            CreateOrderCommand(
                self.facade,
                OrderBuilder()
                .with_order_id("o-602")
                .with_customer_id("c-200")
                .with_store_id("store-2")
                .with_fulfillment(FulfillmentType.DELIVERY)
                .with_amount(500.0),
            )
        )
        self.assertEqual(created.final_amount, 589.0)
        self.assertEqual(len(self.context.observer.sent), 1)  # only push for c-200

    def test_state_transition_and_command(self) -> None:
        self.bus.execute(
            CreateOrderCommand(
                self.facade,
                OrderBuilder()
                .with_order_id("o-603")
                .with_customer_id("c-100")
                .with_store_id("store-1")
                .with_fulfillment(FulfillmentType.PICKUP)
                .with_amount(350.0),
            )
        )
        updated = self.bus.execute(
            ChangeStatusCommand(self.facade, "o-603", OrderStatus.IN_PREPARATION)
        )
        self.assertEqual(updated.status, OrderStatus.IN_PREPARATION)
        self.assertIn(OrderStatus.IN_PREPARATION, updated.history)

    def test_invalid_transition_blocked_by_chain_and_state(self) -> None:
        self.bus.execute(
            CreateOrderCommand(
                self.facade,
                OrderBuilder()
                .with_order_id("o-604")
                .with_customer_id("c-100")
                .with_store_id("store-1")
                .with_fulfillment(FulfillmentType.PICKUP)
                .with_amount(350.0),
            )
        )
        with self.assertRaises(ValueError):
            self.bus.execute(ChangeStatusCommand(self.facade, "o-604", OrderStatus.DELIVERED))

    def test_audit_decorator_produces_entries(self) -> None:
        self.bus.execute(
            CreateOrderCommand(
                self.facade,
                OrderBuilder()
                .with_order_id("o-605")
                .with_customer_id("c-100")
                .with_store_id("store-1")
                .with_fulfillment(FulfillmentType.PICKUP)
                .with_amount(100.0),
            )
        )
        self.assertGreaterEqual(len(self.context.audit_log), 2)
        self.assertTrue(self.context.audit_log[0].startswith("before:"))


if __name__ == "__main__":
    unittest.main()
