from __future__ import annotations

from sandwich_lab6.behavioral import ChangeStatusCommand, CreateOrderCommand
from sandwich_lab6.bootstrap import build_context
from sandwich_lab6.creational import OrderBuilder
from sandwich_lab6.domain import FulfillmentType, OrderStatus


def run_demo() -> None:
    context, bus = build_context()
    facade = context.facade

    order = bus.execute(
        CreateOrderCommand(
            facade,
            OrderBuilder()
            .with_order_id("o-600")
            .with_customer_id("c-100")
            .with_store_id("store-1")
            .with_fulfillment(FulfillmentType.PICKUP)
            .with_amount(450.0),
        )
    )
    print(f"Создан заказ: {order.order_id}, итоговая сумма: {order.final_amount}")

    updated = bus.execute(ChangeStatusCommand(facade, "o-600", OrderStatus.IN_PREPARATION))
    print(f"Статус заказа: {updated.status.value}, история: {[item.value for item in updated.history]}")

    print("Отправленные уведомления:")
    for item in context.observer.sent:
        print(f"- {item.channel} -> {item.recipient}: {item.message}")

    print("Аудит каналов:", context.audit_log)


if __name__ == "__main__":
    run_demo()

