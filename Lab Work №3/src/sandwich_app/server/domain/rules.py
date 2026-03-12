from __future__ import annotations

from sandwich_app.server.domain.models import FulfillmentType, Order, OrderStatus


class InvalidTransitionError(ValueError):
    pass


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


def ensure_transition_allowed(order: Order, new_status: OrderStatus) -> None:
    allowed_next = ALLOWED_TRANSITIONS[order.fulfillment][order.status]
    if new_status not in allowed_next:
        raise InvalidTransitionError(
            f"Нельзя перевести заказ {order.order_id} из {order.status.value} в {new_status.value} "
            f"для сценария {order.fulfillment.value}."
        )
