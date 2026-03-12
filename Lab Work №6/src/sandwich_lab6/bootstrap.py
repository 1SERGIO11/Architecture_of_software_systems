from __future__ import annotations

from sandwich_lab6.behavioral import CommandBus, NotificationObserver, OrderEventPublisher, OrderStateMachine
from sandwich_lab6.creational import AppConfig, EmailChannelCreator, PushChannelCreator
from sandwich_lab6.domain import Customer
from sandwich_lab6.facade import Lab6Context, OrderManagementFacade
from sandwich_lab6.structural import CustomerRepositoryCacheProxy, InMemoryCustomerRepository, InMemoryOrderRepository


def build_context() -> tuple[Lab6Context, CommandBus]:
    config = AppConfig()
    customer_repo = CustomerRepositoryCacheProxy(InMemoryCustomerRepository())
    order_repo = InMemoryOrderRepository()
    publisher = OrderEventPublisher()
    state_machine = OrderStateMachine()
    audit_log: list[str] = []

    observer = NotificationObserver(
        customer_repo=customer_repo,
        creators=[PushChannelCreator(), EmailChannelCreator()],
        audit_log=audit_log,
    )
    publisher.subscribe(observer)

    facade = OrderManagementFacade(
        customer_repo=customer_repo,
        order_repo=order_repo,
        publisher=publisher,
        state_machine=state_machine,
        config=config,
    )
    command_bus = CommandBus()

    # Seed example customers from previous labs domain.
    facade.add_customer(
        Customer(
            customer_id="c-100",
            name="Postman User",
            email="postman@example.com",
            push_token="push-postman",
            push_enabled=True,
            email_enabled=True,
        )
    )
    facade.add_customer(
        Customer(
            customer_id="c-200",
            name="Delivery User",
            email="delivery@example.com",
            push_token="push-delivery",
            push_enabled=True,
            email_enabled=False,
        )
    )

    return Lab6Context(facade=facade, observer=observer, audit_log=audit_log), command_bus

