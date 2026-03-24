from __future__ import annotations

import os
import time
import uuid

import psycopg
import requests

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8001/api/v1")
POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://sandwich:sandwich@127.0.0.1:5432/sandwich?sslmode=disable",
)


def wait_for_api(timeout_seconds: float = 120.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: str | None = None

    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                return
            last_error = f"status={response.status_code}, body={response.text}"
        except requests.RequestException as exc:
            last_error = str(exc)
        time.sleep(2)

    raise AssertionError(f"API is not ready: {last_error}")


def test_health_endpoint() -> None:
    wait_for_api()
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"


def test_duplicate_customer_conflict() -> None:
    wait_for_api()

    suffix = uuid.uuid4().hex[:8]
    customer_id = f"it-dup-{suffix}"

    first = requests.post(
        f"{BASE_URL}/customers",
        json={
            "customer_id": customer_id,
            "name": "Duplicate User",
            "email": "duplicate@example.com",
        },
        timeout=10,
    )
    assert first.status_code == 201, first.text

    second = requests.post(
        f"{BASE_URL}/customers",
        json={
            "customer_id": customer_id,
            "name": "Duplicate User Again",
        },
        timeout=10,
    )
    assert second.status_code == 409
    assert "уже существует" in second.json()["error"]


def test_order_crud_flow_with_postgres() -> None:
    wait_for_api()

    suffix = uuid.uuid4().hex[:8]
    customer_id = f"it-c-{suffix}"
    order_id = f"it-o-{suffix}"

    create_customer = requests.post(
        f"{BASE_URL}/customers",
        json={
            "customer_id": customer_id,
            "name": "Integration User",
            "email": "integration@example.com",
            "push_token": "push-integration",
            "push_enabled": True,
            "email_enabled": True,
        },
        timeout=10,
    )
    assert create_customer.status_code == 201, create_customer.text

    customers_list = requests.get(f"{BASE_URL}/customers", timeout=10)
    assert customers_list.status_code == 200
    items = customers_list.json()["items"]
    assert any(item["customer_id"] == customer_id for item in items)

    create_order = requests.post(
        f"{BASE_URL}/orders",
        json={
            "order_id": order_id,
            "customer_id": customer_id,
            "store_id": "store-integration",
            "fulfillment": "pickup",
            "total_amount": 555.0,
        },
        timeout=10,
    )
    assert create_order.status_code == 201, create_order.text
    assert create_order.json()["status"] == "placed"

    get_order = requests.get(f"{BASE_URL}/orders/{order_id}", timeout=10)
    assert get_order.status_code == 200
    assert get_order.json()["order_id"] == order_id

    put_order = requests.put(
        f"{BASE_URL}/orders/{order_id}",
        json={"total_amount": 777.0},
        timeout=10,
    )
    assert put_order.status_code == 200
    assert put_order.json()["total_amount"] == 777.0

    change_status = requests.post(
        f"{BASE_URL}/orders/{order_id}/status",
        json={"status": "in_preparation"},
        timeout=10,
    )
    assert change_status.status_code == 200
    assert change_status.json()["status"] == "in_preparation"

    notifications = requests.get(f"{BASE_URL}/orders/{order_id}/notifications", timeout=10)
    assert notifications.status_code == 200
    assert len(notifications.json()["items"]) >= 2

    with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT status, total_amount FROM orders WHERE order_id = %s", (order_id,))
            row = cursor.fetchone()
            assert row is not None
            status, amount = row
            assert status == "in_preparation"
            assert float(amount) == 777.0

    delete_order = requests.delete(f"{BASE_URL}/orders/{order_id}", timeout=10)
    assert delete_order.status_code == 204

    get_deleted = requests.get(f"{BASE_URL}/orders/{order_id}", timeout=10)
    assert get_deleted.status_code == 404


def test_invalid_order_requests_are_rejected() -> None:
    wait_for_api()

    suffix = uuid.uuid4().hex[:8]
    customer_id = f"it-invalid-c-{suffix}"
    negative_order_id = f"it-invalid-neg-{suffix}"
    fulfillment_order_id = f"it-invalid-ful-{suffix}"

    create_customer = requests.post(
        f"{BASE_URL}/customers",
        json={
            "customer_id": customer_id,
            "name": "Validation User",
            "email": "validation@example.com",
        },
        timeout=10,
    )
    assert create_customer.status_code == 201, create_customer.text

    negative_amount = requests.post(
        f"{BASE_URL}/orders",
        json={
            "order_id": negative_order_id,
            "customer_id": customer_id,
            "store_id": "store-invalid",
            "fulfillment": "pickup",
            "total_amount": -10,
        },
        timeout=10,
    )
    assert negative_amount.status_code == 400
    assert "не может быть отрицательной" in negative_amount.json()["error"]

    invalid_fulfillment = requests.post(
        f"{BASE_URL}/orders",
        json={
            "order_id": fulfillment_order_id,
            "customer_id": customer_id,
            "store_id": "store-invalid",
            "fulfillment": "drone",
            "total_amount": 250,
        },
        timeout=10,
    )
    assert invalid_fulfillment.status_code == 400
    assert "pickup или delivery" in invalid_fulfillment.json()["error"]

    invalid_filter = requests.get(f"{BASE_URL}/orders?status=broken-status", timeout=10)
    assert invalid_filter.status_code == 400
    assert "Поле status" in invalid_filter.json()["error"]

    with psycopg.connect(POSTGRES_DSN, autocommit=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM orders WHERE order_id IN (%s, %s)",
                (negative_order_id, fulfillment_order_id),
            )
            count = cursor.fetchone()[0]
            assert count == 0
