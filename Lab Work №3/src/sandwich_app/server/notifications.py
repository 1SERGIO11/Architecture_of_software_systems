from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sandwich_app.server.domain.models import Order, OrderStatus
from sandwich_app.server.ports import OutboundNotification


@dataclass(frozen=True)
class StatusTemplate:
    title: str
    body: str


class TemplateRenderer:
    """Единый рендеринг шаблонов уведомлений без дублирования текста."""

    _templates: dict[OrderStatus, StatusTemplate] = {
        OrderStatus.PLACED: StatusTemplate("Заказ принят", "Заказ #{order_id} принят магазином."),
        OrderStatus.IN_PREPARATION: StatusTemplate(
            "Заказ готовится", "Заказ #{order_id} уже в работе."
        ),
        OrderStatus.READY_FOR_PICKUP: StatusTemplate(
            "Заказ готов", "Заказ #{order_id} готов к выдаче."
        ),
        OrderStatus.OUT_FOR_DELIVERY: StatusTemplate(
            "Курьер в пути", "Заказ #{order_id} передан курьеру."
        ),
        OrderStatus.DELIVERED: StatusTemplate(
            "Заказ завершен", "Заказ #{order_id} успешно получен."
        ),
        OrderStatus.CANCELLED: StatusTemplate(
            "Заказ отменен", "Заказ #{order_id} был отменен."
        ),
    }

    def render(self, order: Order) -> str:
        template = self._templates[order.status]
        return f"{template.title}: {template.body.format(order_id=order.order_id)}"


class ConsoleChannel:
    def __init__(self, channel_name: str) -> None:
        self.channel_name = channel_name

    def send(self, message: OutboundNotification) -> None:
        print(f"[{self.channel_name}] {message.recipient}: {message.message}")


class NotificationChannel(Protocol):
    def send(self, message: OutboundNotification) -> None: ...


class NotificationDispatcherImpl:
    """Решает, куда отправлять событие, и возвращает лог отправок."""

    def __init__(
        self,
        renderer: TemplateRenderer,
        channels: dict[str, NotificationChannel] | None = None,
    ) -> None:
        self._renderer = renderer
        self._channels = channels or {
            "push": ConsoleChannel("push"),
            "email": ConsoleChannel("email"),
        }

    def dispatch_status_changed(self, order: Order) -> list[OutboundNotification]:
        text = self._renderer.render(order)
        notifications = [
            OutboundNotification(
                order_id=order.order_id,
                status=order.status,
                channel=channel,
                recipient=recipient,
                message=text,
            )
            for channel, recipient in self._iter_targets(order)
            if channel in self._channels
        ]

        for item in notifications:
            sender = self._channels[item.channel]
            sender.send(item)

        return notifications

    @staticmethod
    def _iter_targets(order: Order) -> list[tuple[str, str]]:
        targets: list[tuple[str, str]] = []
        if order.customer.preference.push_enabled and order.customer.push_token:
            targets.append(("push", order.customer.push_token))
        if order.customer.preference.email_enabled and order.customer.email:
            targets.append(("email", order.customer.email))
        return targets
