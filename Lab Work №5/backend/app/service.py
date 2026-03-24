from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.errors import NotFoundError, ValidationError
from app.models import Customer, FulfillmentType, NotificationPreference, NotificationRecord, Order, OrderStatus
from app.repository import PostgresRepository


ALLOWED_TRANSITIONS: dict[FulfillmentType, dict[OrderStatus, set[OrderStatus]]] = {
    FulfillmentType.PICKUP: {
        OrderStatus.PLACED: {OrderStatus.IN_PREPARATION, OrderStatus.CANCELLED},
        OrderStatus.IN_PREPARATION: {OrderStatus.READY_FOR_PICKUP, OrderStatus.CANCELLED},
        OrderStatus.READY_FOR_PICKUP: {OrderStatus.DELIVERED},
        OrderStatus.DELIVERED: set(),
        OrderStatus.CANCELLED: set(),
    },
    FulfillmentType.DELIVERY: {
        OrderStatus.PLACED: {OrderStatus.IN_PREPARATION, OrderStatus.CANCELLED},
        OrderStatus.IN_PREPARATION: {OrderStatus.READY_FOR_PICKUP, OrderStatus.CANCELLED},
        OrderStatus.READY_FOR_PICKUP: {OrderStatus.OUT_FOR_DELIVERY},
        OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED},
        OrderStatus.DELIVERED: set(),
        OrderStatus.CANCELLED: set(),
    },
}


@dataclass(frozen=True)
class CreateOrderPayload:
    order_id: str
    customer_id: str
    store_id: str
    fulfillment: FulfillmentType
    total_amount: float


class OrderService:
    def __init__(self, repository: PostgresRepository) -> None:
        self._repo = repository

    def create_customer(self, payload: dict[str, object]) -> Customer:
        customer = Customer(
            customer_id=_require_non_empty_str(payload["customer_id"], "customer_id"),
            name=_require_non_empty_str(payload["name"], "name"),
            email=_to_optional_str(payload.get("email")),
            push_token=_to_optional_str(payload.get("push_token")),
            preference=NotificationPreference(
                push_enabled=_to_bool(payload.get("push_enabled", True)),
                email_enabled=_to_bool(payload.get("email_enabled", True)),
            ),
        )
        self._repo.create_customer(customer)
        return customer

    def get_customer(self, customer_id: str) -> Customer:
        customer = self._repo.get_customer(customer_id)
        if customer is None:
            raise NotFoundError(f"Клиент {customer_id} не найден.")
        return customer

    def list_customers(self) -> list[Customer]:
        return self._repo.list_customers()

    def create_order(self, payload: CreateOrderPayload) -> Order:
        customer = self._repo.get_customer(payload.customer_id)
        if customer is None:
            raise ValidationError(
                f"Нельзя создать заказ: клиент {payload.customer_id} не найден."
            )
        if payload.total_amount < 0:
            raise ValidationError("Сумма заказа не может быть отрицательной.")

        order = Order(
            order_id=_require_non_empty_str(payload.order_id, "order_id"),
            customer_id=_require_non_empty_str(payload.customer_id, "customer_id"),
            store_id=_require_non_empty_str(payload.store_id, "store_id"),
            fulfillment=payload.fulfillment,
            total_amount=payload.total_amount,
        )
        self._repo.create_order(order)
        self._create_notifications(order, customer)
        return order

    def list_orders(self, status: str | None = None, customer_id: str | None = None) -> list[Order]:
        if status:
            _parse_status(status)
        return self._repo.list_orders(status=status, customer_id=customer_id)

    def get_order(self, order_id: str) -> Order:
        order = self._repo.get_order(order_id)
        if order is None:
            raise NotFoundError(f"Заказ {order_id} не найден.")
        return order

    def update_order(self, order_id: str, payload: dict[str, object]) -> Order:
        order = self.get_order(order_id)
        changed = False

        if "store_id" in payload:
            order.store_id = _require_non_empty_str(payload["store_id"], "store_id")
            changed = True
        if "fulfillment" in payload:
            order.fulfillment = _parse_fulfillment(payload["fulfillment"])
            changed = True
        if "total_amount" in payload:
            amount = float(payload["total_amount"])
            if amount < 0:
                raise ValidationError("Сумма заказа не может быть отрицательной.")
            order.total_amount = amount
            changed = True

        if changed:
            order.touch()

        self._repo.save_order(order)
        return order

    def change_order_status(self, order_id: str, status: str) -> Order:
        order = self.get_order(order_id)
        new_status = _parse_status(status)

        allowed = ALLOWED_TRANSITIONS[order.fulfillment][order.status]
        if new_status not in allowed:
            raise ValidationError(
                f"Нельзя перевести заказ {order_id} из {order.status.value} в {new_status.value}."
            )

        order.advance_to(new_status)
        self._repo.save_order(order)
        customer = self.get_customer(order.customer_id)
        self._create_notifications(order, customer)
        return order

    def list_notifications(self, order_id: str) -> list[NotificationRecord]:
        self.get_order(order_id)
        return self._repo.list_notifications(order_id)

    def delete_order(self, order_id: str) -> None:
        self._repo.delete_order(order_id)

    def ping(self) -> None:
        self._repo.ping()

    def _create_notifications(self, order: Order, customer: Customer) -> list[NotificationRecord]:
        text = _render_message(order)
        targets: list[tuple[str, str]] = []

        if customer.preference.push_enabled and customer.push_token:
            targets.append(("push", customer.push_token))
        if customer.preference.email_enabled and customer.email:
            targets.append(("email", customer.email))

        created: list[NotificationRecord] = []
        for channel, recipient in targets:
            item = NotificationRecord(
                notification_id=str(uuid.uuid4()),
                order_id=order.order_id,
                channel=channel,
                recipient=recipient,
                message=text,
            )
            self._repo.create_notification(item)
            created.append(item)

        return created


def _to_optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _require_non_empty_str(value: object, field_name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValidationError(f"Поле {field_name} обязательно и не должно быть пустым.")
    return text


def _parse_status(value: str) -> OrderStatus:
    try:
        return OrderStatus(value)
    except ValueError as exc:
        raise ValidationError(
            "Поле status должно быть одним из значений: "
            "placed, in_preparation, ready_for_pickup, out_for_delivery, delivered, cancelled."
        ) from exc


def _parse_fulfillment(value: object) -> FulfillmentType:
    text = _require_non_empty_str(value, "fulfillment")
    try:
        return FulfillmentType(text)
    except ValueError as exc:
        raise ValidationError("Поле fulfillment должно быть pickup или delivery.") from exc


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
        raise ValidationError(f"Некорректный булев флаг: {value!r}")
    if isinstance(value, int):
        return value != 0
    raise ValidationError(f"Некорректный булев флаг: {value!r}")


def _render_message(order: Order) -> str:
    titles = {
        OrderStatus.PLACED: "Заказ принят",
        OrderStatus.IN_PREPARATION: "Заказ готовится",
        OrderStatus.READY_FOR_PICKUP: "Заказ готов",
        OrderStatus.OUT_FOR_DELIVERY: "Курьер в пути",
        OrderStatus.DELIVERED: "Заказ доставлен",
        OrderStatus.CANCELLED: "Заказ отменен",
    }
    return f"{titles[order.status]}: заказ #{order.order_id}, статус {order.status.value}."
