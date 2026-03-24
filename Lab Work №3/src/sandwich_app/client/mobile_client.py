from __future__ import annotations

import json
import time
from dataclasses import dataclass
from urllib.request import Request, urlopen


@dataclass
class MobileAppClient:
    base_url: str

    def create_order(
        self,
        order_id: str,
        store_id: str,
        customer_id: str,
        customer_name: str,
        email: str,
        push_token: str,
        fulfillment: str = "pickup",
        total_amount: float = 0.0,
    ) -> dict[str, object]:
        payload = {
            "order_id": order_id,
            "store_id": store_id,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "email": email,
            "push_token": push_token,
            "fulfillment": fulfillment,
            "total_amount": total_amount,
        }
        return self._post("/orders", payload)

    def update_status(self, order_id: str, status: str) -> dict[str, object]:
        return self._post(f"/orders/{order_id}/status", {"status": status})

    def get_order(self, order_id: str) -> dict[str, object]:
        return self._get(f"/orders/{order_id}")

    def wait_for_status(
        self,
        order_id: str,
        expected_status: str,
        timeout_seconds: float = 5.0,
        interval_seconds: float = 0.25,
    ) -> dict[str, object]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            snapshot = self.get_order(order_id)
            if snapshot.get("status") == expected_status:
                return snapshot
            time.sleep(interval_seconds)

        raise TimeoutError(
            f"Заказ {order_id} не перешел в статус {expected_status} за {timeout_seconds} сек."
        )

    def _post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            url=f"{self.base_url}{path}",
            method="POST",
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get(self, path: str) -> dict[str, object]:
        request = Request(url=f"{self.base_url}{path}", method="GET")
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))


def demo() -> None:
    client = MobileAppClient("http://127.0.0.1:8000")
    created = client.create_order(
        order_id="demo-1",
        store_id="store-42",
        customer_id="customer-1",
        customer_name="Demo User",
        email="demo@example.com",
        push_token="push-demo",
        fulfillment="pickup",
        total_amount=450.0,
    )
    print("Создан заказ:", created)

    updated = client.update_status("demo-1", "in_preparation")
    print("Обновлен статус:", updated["status"])


def main() -> None:
    print("Ожидается, что сервер уже запущен на http://127.0.0.1:8000")
    demo()


if __name__ == "__main__":
    main()
