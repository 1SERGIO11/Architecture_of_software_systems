from __future__ import annotations

from sandwich_lab6.behavioral import (
    CustomerExistsValidator,
    DeliveryPricingStrategy,
    NotificationObserver,
    OrderEventPublisher,
    OrderStateMachine,
    PickupPricingStrategy,
    PositiveAmountValidator,
    PricingStrategy,
    StatusTransitionValidator,
    ValidationContext,
)
from sandwich_lab6.creational import AppConfig, OrderBuilder
from sandwich_lab6.domain import Customer, FulfillmentType, Order, OrderEvent, OrderStatus
from sandwich_lab6.ports import CustomerRepository, OrderRepository


class OrderManagementFacade:
    """Facade coordinates business scenario of order lifecycle."""

    def __init__(
        self,
        customer_repo: CustomerRepository,
        order_repo: OrderRepository,
        publisher: OrderEventPublisher,
        state_machine: OrderStateMachine,
        config: AppConfig,
    ) -> None:
        self._customer_repo = customer_repo
        self._order_repo = order_repo
        self._publisher = publisher
        self._state_machine = state_machine
        self._config = config
        self._pricing: dict[FulfillmentType, PricingStrategy] = {
            FulfillmentType.PICKUP: PickupPricingStrategy(),
            FulfillmentType.DELIVERY: DeliveryPricingStrategy(config.delivery_fee),
        }

    def add_customer(self, customer: Customer) -> None:
        self._customer_repo.add(customer)

    def list_customers(self) -> list[Customer]:
        return self._customer_repo.list()

    def list_orders(self) -> list[Order]:
        return self._order_repo.list()

    def create_order(self, builder: OrderBuilder) -> Order:
        order = builder.build()
        validation = CustomerExistsValidator(self._customer_repo)
        validation.set_next(PositiveAmountValidator())
        validation.handle(ValidationContext(order=order))

        strategy = self._pricing[order.fulfillment]
        order.final_amount = strategy.calculate(order.base_amount)
        self._order_repo.save(order)
        self._publisher.publish(
            OrderEvent(
                order_id=order.order_id,
                customer_id=order.customer_id,
                status=order.status,
                text=f"Заказ #{order.order_id} создан со статусом {order.status.value}.",
            )
        )
        return order

    def change_order_status(self, order_id: str, target_status: OrderStatus) -> Order:
        order = self._order_repo.get(order_id)
        if order is None:
            raise ValueError(f"Заказ {order_id} не найден.")

        validation = StatusTransitionValidator(self._state_machine)
        validation.handle(ValidationContext(order=order, target_status=target_status))

        self._state_machine.transition(order, target_status)
        self._order_repo.save(order)
        self._publisher.publish(
            OrderEvent(
                order_id=order.order_id,
                customer_id=order.customer_id,
                status=order.status,
                text=f"Заказ #{order.order_id} переведен в статус {order.status.value}.",
            )
        )
        return order


class Lab6Context:
    def __init__(
        self,
        facade: OrderManagementFacade,
        observer: NotificationObserver,
        audit_log: list[str],
    ) -> None:
        self.facade = facade
        self.observer = observer
        self.audit_log = audit_log

