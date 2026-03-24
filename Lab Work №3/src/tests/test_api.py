from __future__ import annotations

import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sandwich_app.server.api import build_http_server


class ApiIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = build_http_server(host="127.0.0.1", port=0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)

    def test_create_and_update_order(self) -> None:
        created = self._post(
            "/orders",
            {
                "order_id": "api-1",
                "store_id": "store-1",
                "customer_id": "c-101",
                "customer_name": "Bob",
                "email": "bob@example.com",
                "push_token": "push-bob",
                "fulfillment": "delivery",
                "total_amount": 540.0,
            },
        )
        self.assertEqual(created["status"], "placed")

        updated = self._post("/orders/api-1/status", {"status": "in_preparation"})
        self.assertEqual(updated["status"], "in_preparation")
        self.assertEqual(len(updated["sent_notifications"]), 2)

        fetched = self._get("/orders/api-1")
        self.assertEqual(fetched["status"], "in_preparation")

    def test_duplicate_order_returns_conflict(self) -> None:
        payload = {
            "order_id": "api-dup",
            "store_id": "store-1",
            "customer_id": "c-102",
            "customer_name": "Eve",
            "email": "eve@example.com",
            "push_token": "push-eve",
        }

        self._post("/orders", payload)

        with self.assertRaises(HTTPError) as exc:
            self._post("/orders", payload)

        self.assertEqual(exc.exception.code, 409)
        exc.exception.close()

    def _post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{self.port}{path}",
            method="POST",
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get(self, path: str) -> dict[str, object]:
        request = Request(f"http://127.0.0.1:{self.port}{path}", method="GET")
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
