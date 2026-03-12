from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from sandwich_lab6.creational import NotificationChannelCreator, OrderBuilder
from sandwich_lab6.domain import Customer, FulfillmentType, NotificationMessage, Order, OrderEvent, OrderStatus
from sandwich_lab6.ports import CustomerRepository

if TYPE_CHECKING:
    from sandwich_lab6.facade import OrderManagementFacade


class PricingStrategy(ABC):
    @abstractmethod
    def calculate(self, base_amount: float) -> float:
        raise NotImplementedError


class PickupPricingStrategy(PricingStrategy):
    def calculate(self, base_amount: float) -> float:
        return round(base_amount, 2)


class DeliveryPricingStrategy(PricingStrategy):
    def __init__(self, delivery_fee: float) -> None:
        self._delivery_fee = delivery_fee

    def calculate(self, base_amount: float) -> float:
        return round(base_amount + self._delivery_fee, 2)


class OrderEventObserver(ABC):
    @abstractmethod
    def update(self, event: OrderEvent) -> None:
        raise NotImplementedError


class OrderEventPublisher:
    def __init__(self) -> None:
        self._subscribers: list[OrderEventObserver] = []

    def subscribe(self, subscriber: OrderEventObserver) -> None:
        self._subscribers.append(subscriber)

    def publish(self, event: OrderEvent) -> None:
        for subscriber in self._subscribers:
            subscriber.update(event)


class NotificationObserver(OrderEventObserver):
    def __init__(
        self,
        customer_repo: CustomerRepository,
        creators: list[NotificationChannelCreator],
        audit_log: list[str],
    ) -> None:
        self._customer_repo = customer_repo
        self._creators = creators
        self._audit_log = audit_log
        self.sent: list[NotificationMessage] = []

    def update(self, event: OrderEvent) -> None:
        customer = self._customer_repo.get(event.customer_id)
        if customer is None:
            return
        for creator in self._creators:
            channel = creator.create_audited_channel(self._audit_log)
            recipient = self._resolve_recipient(customer, channel.channel_name)
            if not recipient:
                continue
            channel.send(recipient, event.text)
            self.sent.append(
                NotificationMessage(
                    order_id=event.order_id,
                    channel=channel.channel_name,
                    recipient=recipient,
                    message=event.text,
                )
            )

    def _resolve_recipient(self, customer: Customer, channel_name: str) -> str | None:
        if channel_name == "push" and customer.push_enabled:
            return customer.push_token
        if channel_name == "email" and customer.email_enabled:
            return customer.email
        return None


class OrderState(ABC):
    status: OrderStatus

    @abstractmethod
    def next_statuses(self, fulfillment: FulfillmentType) -> set[OrderStatus]:
        raise NotImplementedError


class PlacedState(OrderState):
    status = OrderStatus.PLACED

    def next_statuses(self, fulfillment: FulfillmentType) -> set[OrderStatus]:
        return {OrderStatus.IN_PREPARATION, OrderStatus.CANCELLED}


class InPreparationState(OrderState):
    status = OrderStatus.IN_PREPARATION

    def next_statuses(self, fulfillment: FulfillmentType) -> set[OrderStatus]:
        return {OrderStatus.READY_FOR_PICKUP, OrderStatus.CANCELLED}


class ReadyForPickupState(OrderState):
    status = OrderStatus.READY_FOR_PICKUP

    def next_statuses(self, fulfillment: FulfillmentType) -> set[OrderStatus]:
        if fulfillment == FulfillmentType.DELIVERY:
            return {OrderStatus.OUT_FOR_DELIVERY}
        return {OrderStatus.DELIVERED}


class OutForDeliveryState(OrderState):
    status = OrderStatus.OUT_FOR_DELIVERY

    def next_statuses(self, fulfillment: FulfillmentType) -> set[OrderStatus]:
        return {OrderStatus.DELIVERED}


class DeliveredState(OrderState):
    status = OrderStatus.DELIVERED

    def next_statuses(self, fulfillment: FulfillmentType) -> set[OrderStatus]:
        return set()


class CancelledState(OrderState):
    status = OrderStatus.CANCELLED

    def next_statuses(self, fulfillment: FulfillmentType) -> set[OrderStatus]:
        return set()


class OrderStateMachine:
    def __init__(self) -> None:
        self._states: dict[OrderStatus, OrderState] = {
            OrderStatus.PLACED: PlacedState(),
            OrderStatus.IN_PREPARATION: InPreparationState(),
            OrderStatus.READY_FOR_PICKUP: ReadyForPickupState(),
            OrderStatus.OUT_FOR_DELIVERY: OutForDeliveryState(),
            OrderStatus.DELIVERED: DeliveredState(),
            OrderStatus.CANCELLED: CancelledState(),
        }

    def can_transition(self, order: Order, target: OrderStatus) -> bool:
        state = self._states[order.status]
        return target in state.next_statuses(order.fulfillment)

    def transition(self, order: Order, target: OrderStatus) -> None:
        if not self.can_transition(order, target):
            raise ValueError(
                f"Недопустимый переход статуса: {order.status.value} -> {target.value}."
            )
        order.set_status(target)


@dataclass
class ValidationContext:
    order: Order | None = None
    target_status: OrderStatus | None = None


class ValidationHandler(ABC):
    def __init__(self) -> None:
        self._next: ValidationHandler | None = None

    def set_next(self, handler: ValidationHandler) -> ValidationHandler:
        self._next = handler
        return handler

    def handle(self, context: ValidationContext) -> None:
        self._handle_current(context)
        if self._next:
            self._next.handle(context)

    @abstractmethod
    def _handle_current(self, context: ValidationContext) -> None:
        raise NotImplementedError


class CustomerExistsValidator(ValidationHandler):
    def __init__(self, customer_repo: CustomerRepository) -> None:
        super().__init__()
        self._customer_repo = customer_repo

    def _handle_current(self, context: ValidationContext) -> None:
        if context.order is None:
            raise ValueError("Нет заказа для проверки клиента.")
        if self._customer_repo.get(context.order.customer_id) is None:
            raise ValueError(f"Клиент {context.order.customer_id} не найден.")


class PositiveAmountValidator(ValidationHandler):
    def _handle_current(self, context: ValidationContext) -> None:
        if context.order is None:
            raise ValueError("Нет заказа для проверки суммы.")
        if context.order.base_amount <= 0:
            raise ValueError("Сумма заказа должна быть положительной.")


class StatusTransitionValidator(ValidationHandler):
    def __init__(self, state_machine: OrderStateMachine) -> None:
        super().__init__()
        self._state_machine = state_machine

    def _handle_current(self, context: ValidationContext) -> None:
        if context.order is None or context.target_status is None:
            raise ValueError("Нет данных для проверки перехода статуса.")
        if not self._state_machine.can_transition(context.order, context.target_status):
            raise ValueError(
                f"Недопустимый переход {context.order.status.value} -> {context.target_status.value}."
            )


class Command(ABC):
    @abstractmethod
    def execute(self) -> object:
        raise NotImplementedError


class CreateOrderCommand(Command):
    def __init__(self, facade: OrderManagementFacade, builder: OrderBuilder) -> None:
        self._facade = facade
        self._builder = builder

    def execute(self) -> Order:
        return self._facade.create_order(self._builder)


class ChangeStatusCommand(Command):
    def __init__(self, facade: OrderManagementFacade, order_id: str, status: OrderStatus) -> None:
        self._facade = facade
        self._order_id = order_id
        self._status = status

    def execute(self) -> Order:
        return self._facade.change_order_status(self._order_id, self._status)


class CommandBus:
    def __init__(self, after_execute: Callable[[Command], None] | None = None) -> None:
        self._after_execute = after_execute

    def execute(self, command: Command) -> object:
        result = command.execute()
        if self._after_execute:
            self._after_execute(command)
        return result

