from __future__ import annotations

import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from order_api.api import build_server


class RestApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = build_server(host="127.0.0.1", port=0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)

    def test_health(self) -> None:
        response = self._get("/api/v1/health")
        self.assertEqual(response["status"], "ok")

    def test_customers_create_and_get(self) -> None:
        created = self._post(
            "/api/v1/customers",
            {
                "customer_id": "c-1",
                "name": "Alice",
                "email": "alice@example.com",
                "push_token": "push-alice",
            },
        )
        self.assertEqual(created["customer_id"], "c-1")

        fetched = self._get("/api/v1/customers/c-1")
        self.assertEqual(fetched["name"], "Alice")

    def test_create_customer_duplicate(self) -> None:
        payload = {"customer_id": "c-2", "name": "Bob"}
        self._post("/api/v1/customers", payload)

        with self.assertRaises(HTTPError) as exc:
            self._post("/api/v1/customers", payload)

        self.assertEqual(exc.exception.code, 409)
        exc.exception.close()

    def test_orders_crud_and_notifications(self) -> None:
        self._post(
            "/api/v1/customers",
            {
                "customer_id": "c-3",
                "name": "Eve",
                "email": "eve@example.com",
                "push_token": "push-eve",
            },
        )

        order = self._post(
            "/api/v1/orders",
            {
                "order_id": "o-1",
                "customer_id": "c-3",
                "store_id": "store-1",
                "fulfillment": "pickup",
                "total_amount": 250,
            },
        )
        self.assertEqual(order["status"], "placed")
        created_updated_at = order["updated_at"]

        updated = self._put("/api/v1/orders/o-1", {"total_amount": 400})
        self.assertEqual(updated["total_amount"], 400)
        self.assertNotEqual(updated["updated_at"], created_updated_at)

        transitioned = self._post("/api/v1/orders/o-1/status", {"status": "in_preparation"})
        self.assertEqual(transitioned["status"], "in_preparation")

        notifications = self._get("/api/v1/orders/o-1/notifications")
        self.assertGreaterEqual(len(notifications["items"]), 2)

        listing = self._get("/api/v1/orders?status=in_preparation")
        self.assertEqual(len(listing["items"]), 1)

        status, _, _ = self._delete("/api/v1/orders/o-1")
        self.assertEqual(status, 204)

        with self.assertRaises(HTTPError) as exc:
            self._get("/api/v1/orders/o-1")
        self.assertEqual(exc.exception.code, 404)
        exc.exception.close()

    def test_invalid_status_transition(self) -> None:
        self._post(
            "/api/v1/customers",
            {
                "customer_id": "c-4",
                "name": "Dan",
                "email": "dan@example.com",
                "push_token": "push-dan",
            },
        )
        self._post(
            "/api/v1/orders",
            {
                "order_id": "o-4",
                "customer_id": "c-4",
                "store_id": "store-1",
                "fulfillment": "pickup",
                "total_amount": 200,
            },
        )

        with self.assertRaises(HTTPError) as exc:
            self._post("/api/v1/orders/o-4/status", {"status": "delivered"})

        self.assertEqual(exc.exception.code, 400)
        exc.exception.close()

    def test_create_order_unknown_customer(self) -> None:
        with self.assertRaises(HTTPError) as exc:
            self._post(
                "/api/v1/orders",
                {
                    "order_id": "o-404",
                    "customer_id": "unknown",
                    "store_id": "store-1",
                    "fulfillment": "pickup",
                    "total_amount": 100,
                },
            )
        self.assertEqual(exc.exception.code, 400)
        exc.exception.close()

    def test_create_order_negative_amount(self) -> None:
        self._post(
            "/api/v1/customers",
            {
                "customer_id": "c-neg",
                "name": "Negative",
            },
        )

        with self.assertRaises(HTTPError) as exc:
            self._post(
                "/api/v1/orders",
                {
                    "order_id": "o-neg",
                    "customer_id": "c-neg",
                    "store_id": "store-1",
                    "fulfillment": "pickup",
                    "total_amount": -1,
                },
            )

        self.assertEqual(exc.exception.code, 400)
        exc.exception.close()

    def test_update_order_invalid_fulfillment(self) -> None:
        self._post(
            "/api/v1/customers",
            {
                "customer_id": "c-ful",
                "name": "Fulfillment",
            },
        )
        self._post(
            "/api/v1/orders",
            {
                "order_id": "o-ful",
                "customer_id": "c-ful",
                "store_id": "store-1",
                "fulfillment": "pickup",
                "total_amount": 100,
            },
        )

        with self.assertRaises(HTTPError) as exc:
            self._put("/api/v1/orders/o-ful", {"fulfillment": "drone"})

        self.assertEqual(exc.exception.code, 400)
        exc.exception.close()

    def _base(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def _get(self, path: str) -> dict[str, object]:
        request = Request(self._base(path), method="GET")
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def _post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            self._base(path),
            method="POST",
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def _put(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            self._base(path),
            method="PUT",
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def _delete(self, path: str) -> tuple[int, bytes, dict[str, str]]:
        request = Request(self._base(path), method="DELETE")
        with urlopen(request) as response:
            return response.status, response.read(), dict(response.headers)


if __name__ == "__main__":
    unittest.main()
