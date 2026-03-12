from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from sandwich_lab6.domain import FulfillmentType, Order
from sandwich_lab6.ports import NotificationChannel


class AppConfig:
    """Singleton configuration for pricing and message templates."""

    _instance: AppConfig | None = None

    def __new__(cls) -> AppConfig:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.delivery_fee = 89.0
            cls._instance.currency = "RUB"
        return cls._instance


@dataclass
class OrderBuilder:
    """Builder for step-by-step order creation."""

    _order_id: str | None = None
    _customer_id: str | None = None
    _store_id: str | None = None
    _fulfillment: FulfillmentType = FulfillmentType.PICKUP
    _amount: float = 0.0

    def with_order_id(self, order_id: str) -> OrderBuilder:
        self._order_id = order_id
        return self

    def with_customer_id(self, customer_id: str) -> OrderBuilder:
        self._customer_id = customer_id
        return self

    def with_store_id(self, store_id: str) -> OrderBuilder:
        self._store_id = store_id
        return self

    def with_fulfillment(self, fulfillment: FulfillmentType) -> OrderBuilder:
        self._fulfillment = fulfillment
        return self

    def with_amount(self, amount: float) -> OrderBuilder:
        self._amount = amount
        return self

    def build(self) -> Order:
        if not self._order_id or not self._customer_id or not self._store_id:
            raise ValueError("Для создания заказа нужны order_id, customer_id и store_id.")
        return Order(
            order_id=self._order_id,
            customer_id=self._customer_id,
            store_id=self._store_id,
            fulfillment=self._fulfillment,
            base_amount=self._amount,
        )


class NotificationChannelCreator(ABC):
    """Factory Method: each creator constructs one channel family."""

    @abstractmethod
    def create_channel(self) -> NotificationChannel:
        raise NotImplementedError

    def create_audited_channel(self, audit_log: list[str]) -> NotificationChannel:
        from sandwich_lab6.structural import AuditNotificationDecorator

        return AuditNotificationDecorator(self.create_channel(), audit_log)


class EmailChannelCreator(NotificationChannelCreator):
    def create_channel(self) -> NotificationChannel:
        from sandwich_lab6.structural import EmailGatewayAdapter, LegacyEmailGateway

        return EmailGatewayAdapter(LegacyEmailGateway())


class PushChannelCreator(NotificationChannelCreator):
    def create_channel(self) -> NotificationChannel:
        from sandwich_lab6.structural import LegacyPushGateway, PushGatewayAdapter

        return PushGatewayAdapter(LegacyPushGateway())

