from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class FulfillmentType(str, Enum):
    PICKUP = "pickup"
    DELIVERY = "delivery"


class OrderStatus(str, Enum):
    PLACED = "placed"
    IN_PREPARATION = "in_preparation"
    READY_FOR_PICKUP = "ready_for_pickup"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Customer:
    customer_id: str
    name: str
    email: str | None = None
    push_token: str | None = None
    push_enabled: bool = True
    email_enabled: bool = True


@dataclass
class Order:
    order_id: str
    customer_id: str
    store_id: str
    fulfillment: FulfillmentType
    base_amount: float
    final_amount: float = 0.0
    status: OrderStatus = OrderStatus.PLACED
    history: list[OrderStatus] = field(default_factory=lambda: [OrderStatus.PLACED])
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def set_status(self, status: OrderStatus) -> None:
        self.status = status
        self.history.append(status)
        self.updated_at = datetime.now(timezone.utc)


@dataclass(frozen=True)
class NotificationMessage:
    order_id: str
    channel: str
    recipient: str
    message: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class OrderEvent:
    order_id: str
    customer_id: str
    status: OrderStatus
    text: str

