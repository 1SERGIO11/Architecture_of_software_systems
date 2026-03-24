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
class NotificationPreference:
    push_enabled: bool = True
    email_enabled: bool = True


@dataclass(frozen=True)
class CustomerContact:
    customer_id: str
    name: str
    push_token: str | None = None
    email: str | None = None
    preference: NotificationPreference = field(default_factory=NotificationPreference)


@dataclass
class Order:
    order_id: str
    customer: CustomerContact
    store_id: str
    fulfillment: FulfillmentType
    total_amount: float
    statuses: list[OrderStatus] = field(default_factory=lambda: [OrderStatus.PLACED])
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def status(self) -> OrderStatus:
        return self.statuses[-1]

    @property
    def history(self) -> tuple[OrderStatus, ...]:
        return tuple(self.statuses)

    def advance_to(self, new_status: OrderStatus) -> None:
        self.statuses.append(new_status)
        self.updated_at = datetime.now(timezone.utc)
