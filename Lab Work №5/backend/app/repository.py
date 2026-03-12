from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from app.errors import ConflictError, NotFoundError
from app.models import (
    Customer,
    FulfillmentType,
    NotificationPreference,
    NotificationRecord,
    Order,
    OrderStatus,
)


class PostgresRepository:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def bootstrap(self, retries: int = 30, delay_seconds: float = 1.0) -> None:
        for attempt in range(1, retries + 1):
            try:
                self.ping()
                self._init_schema()
                return
            except Exception:
                if attempt == retries:
                    raise
                time.sleep(delay_seconds)

    def ping(self) -> None:
        with psycopg.connect(self._dsn, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")

    def _init_schema(self) -> None:
        with psycopg.connect(self._dsn, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS customers (
                        customer_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT,
                        push_token TEXT,
                        push_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        email_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS orders (
                        order_id TEXT PRIMARY KEY,
                        customer_id TEXT NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
                        store_id TEXT NOT NULL,
                        fulfillment TEXT NOT NULL,
                        status TEXT NOT NULL,
                        history JSONB NOT NULL,
                        total_amount DOUBLE PRECISION NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS notifications (
                        notification_id TEXT PRIMARY KEY,
                        order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
                        channel TEXT NOT NULL,
                        recipient TEXT NOT NULL,
                        message TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                )

    def create_customer(self, customer: Customer) -> None:
        if self.get_customer(customer.customer_id):
            raise ConflictError(f"Клиент {customer.customer_id} уже существует.")

        with psycopg.connect(self._dsn, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO customers (customer_id, name, email, push_token, push_enabled, email_enabled)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        customer.customer_id,
                        customer.name,
                        customer.email,
                        customer.push_token,
                        customer.preference.push_enabled,
                        customer.preference.email_enabled,
                    ),
                )

    def get_customer(self, customer_id: str) -> Customer | None:
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT customer_id, name, email, push_token, push_enabled, email_enabled
                    FROM customers WHERE customer_id = %s
                    """,
                    (customer_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return Customer(
                    customer_id=row["customer_id"],
                    name=row["name"],
                    email=row["email"],
                    push_token=row["push_token"],
                    preference=NotificationPreference(
                        push_enabled=bool(row["push_enabled"]),
                        email_enabled=bool(row["email_enabled"]),
                    ),
                )

    def list_customers(self) -> list[Customer]:
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT customer_id, name, email, push_token, push_enabled, email_enabled
                    FROM customers
                    ORDER BY customer_id ASC
                    """
                )
                rows = cursor.fetchall()
                return [
                    Customer(
                        customer_id=row["customer_id"],
                        name=row["name"],
                        email=row["email"],
                        push_token=row["push_token"],
                        preference=NotificationPreference(
                            push_enabled=bool(row["push_enabled"]),
                            email_enabled=bool(row["email_enabled"]),
                        ),
                    )
                    for row in rows
                ]

    def create_order(self, order: Order) -> None:
        if self.get_order(order.order_id):
            raise ConflictError(f"Заказ {order.order_id} уже существует.")

        with psycopg.connect(self._dsn, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO orders (order_id, customer_id, store_id, fulfillment, status, history, total_amount, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        order.order_id,
                        order.customer_id,
                        order.store_id,
                        order.fulfillment.value,
                        order.status.value,
                        Json([item.value for item in order.history]),
                        order.total_amount,
                        order.updated_at,
                    ),
                )

    def get_order(self, order_id: str) -> Order | None:
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT order_id, customer_id, store_id, fulfillment, status, history, total_amount, updated_at
                    FROM orders WHERE order_id = %s
                    """,
                    (order_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return _row_to_order(row)

    def list_orders(self, status: str | None = None, customer_id: str | None = None) -> list[Order]:
        conditions: list[str] = []
        params: list[object] = []

        if status:
            conditions.append("status = %s")
            params.append(status)
        if customer_id:
            conditions.append("customer_id = %s")
            params.append(customer_id)

        query = (
            "SELECT order_id, customer_id, store_id, fulfillment, status, history, total_amount, updated_at FROM orders"
        )
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY updated_at DESC"

        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [_row_to_order(row) for row in rows]

    def save_order(self, order: Order) -> None:
        with psycopg.connect(self._dsn, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE orders
                    SET store_id = %s,
                        fulfillment = %s,
                        status = %s,
                        history = %s,
                        total_amount = %s,
                        updated_at = %s
                    WHERE order_id = %s
                    """,
                    (
                        order.store_id,
                        order.fulfillment.value,
                        order.status.value,
                        Json([item.value for item in order.history]),
                        order.total_amount,
                        order.updated_at,
                        order.order_id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise NotFoundError(f"Заказ {order.order_id} не найден.")

    def delete_order(self, order_id: str) -> None:
        with psycopg.connect(self._dsn, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))
                if cursor.rowcount == 0:
                    raise NotFoundError(f"Заказ {order_id} не найден.")

    def create_notification(self, item: NotificationRecord) -> None:
        with psycopg.connect(self._dsn, autocommit=True) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO notifications (notification_id, order_id, channel, recipient, message, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        item.notification_id,
                        item.order_id,
                        item.channel,
                        item.recipient,
                        item.message,
                        item.created_at,
                    ),
                )

    def list_notifications(self, order_id: str) -> list[NotificationRecord]:
        with psycopg.connect(self._dsn, autocommit=True, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT notification_id, order_id, channel, recipient, message, created_at
                    FROM notifications
                    WHERE order_id = %s
                    ORDER BY created_at ASC
                    """,
                    (order_id,),
                )
                rows = cursor.fetchall()
                return [
                    NotificationRecord(
                        notification_id=row["notification_id"],
                        order_id=row["order_id"],
                        channel=row["channel"],
                        recipient=row["recipient"],
                        message=row["message"],
                        created_at=row["created_at"],
                    )
                    for row in rows
                ]


def _row_to_order(row: dict[str, object]) -> Order:
    raw_history = row["history"]
    if isinstance(raw_history, str):
        history_values = json.loads(raw_history)
    else:
        history_values = list(raw_history)

    statuses = [OrderStatus(item) for item in history_values]
    return Order(
        order_id=str(row["order_id"]),
        customer_id=str(row["customer_id"]),
        store_id=str(row["store_id"]),
        fulfillment=FulfillmentType(str(row["fulfillment"])),
        total_amount=float(row["total_amount"]),
        statuses=statuses,
        updated_at=_to_datetime(row["updated_at"]),
    )


def _to_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return datetime.now(timezone.utc)
