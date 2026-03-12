from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from sandwich_app.server.domain.models import (
    CustomerContact,
    FulfillmentType,
    NotificationPreference,
    Order,
    OrderStatus,
)
from sandwich_app.server.notifications import NotificationDispatcherImpl, TemplateRenderer
from sandwich_app.server.repositories.in_memory import InMemoryOrderRepository
from sandwich_app.server.services.order_status_service import (
    OrderAlreadyExistsError,
    OrderNotFoundError,
    OrderStatusService,
)


class App:
    def __init__(self) -> None:
        self.service = OrderStatusService(
            orders=InMemoryOrderRepository(),
            notifier=NotificationDispatcherImpl(renderer=TemplateRenderer()),
        )

    def create_order(self, payload: dict[str, object]) -> dict[str, object]:
        order = Order(
            order_id=str(payload["order_id"]),
            store_id=str(payload["store_id"]),
            fulfillment=FulfillmentType(str(payload.get("fulfillment", "pickup"))),
            total_amount=float(payload.get("total_amount", 0.0)),
            customer=CustomerContact(
                customer_id=str(payload["customer_id"]),
                name=str(payload.get("customer_name", "Unknown")),
                push_token=_to_optional_str(payload.get("push_token")),
                email=_to_optional_str(payload.get("email")),
                preference=NotificationPreference(
                    push_enabled=_to_bool(payload.get("push_enabled", True)),
                    email_enabled=_to_bool(payload.get("email_enabled", True)),
                ),
            ),
        )

        self.service.create_order(order)
        return order_to_dict(order)

    def update_status(self, order_id: str, payload: dict[str, object]) -> dict[str, object]:
        status = OrderStatus(str(payload["status"]))
        result = self.service.update_status(order_id=order_id, new_status=status)
        response = order_to_dict(result.order)
        response["sent_notifications"] = [
            {
                "channel": n.channel,
                "recipient": n.recipient,
                "message": n.message,
                "status": n.status.value,
            }
            for n in result.notifications
        ]
        return response

    def get_order(self, order_id: str) -> dict[str, object]:
        order = self.service.get_order(order_id)
        return order_to_dict(order)


def order_to_dict(order: Order) -> dict[str, object]:
    return {
        "order_id": order.order_id,
        "store_id": order.store_id,
        "fulfillment": order.fulfillment.value,
        "status": order.status.value,
        "history": [state.value for state in order.history],
        "updated_at": order.updated_at.isoformat(),
        "total_amount": order.total_amount,
        "customer": {
            "customer_id": order.customer.customer_id,
            "name": order.customer.name,
            "email": order.customer.email,
            "push_token": order.customer.push_token,
        },
    }


def _to_optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
        raise ValueError(f"Некорректный булев флаг: {value!r}")
    if isinstance(value, int):
        return value != 0
    raise ValueError(f"Некорректный булев флаг: {value!r}")


def make_handler(app: App) -> type[BaseHTTPRequestHandler]:
    class ApiHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            body = self._read_json_body()

            try:
                if parsed.path == "/orders":
                    self._send_json(app.create_order(body), HTTPStatus.CREATED)
                    return

                if parsed.path.startswith("/orders/") and parsed.path.endswith("/status"):
                    order_id = parsed.path.split("/")[2]
                    self._send_json(app.update_status(order_id, body), HTTPStatus.OK)
                    return

                self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            except KeyError as exc:
                self._send_json({"error": f"missing_field:{exc.args[0]}"}, HTTPStatus.BAD_REQUEST)
            except OrderAlreadyExistsError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.CONFLICT)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except OrderNotFoundError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            try:
                if parsed.path.startswith("/orders/"):
                    order_id = parsed.path.split("/")[2]
                    self._send_json(app.get_order(order_id), HTTPStatus.OK)
                    return

                self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            except OrderNotFoundError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            # Тишина в тестах и локальном запуске.
            return

        def _read_json_body(self) -> dict[str, object]:
            size = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(size) if size else b"{}"
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("JSON body должен быть объектом.")
            return data

        def _send_json(self, payload: dict[str, object], status: HTTPStatus) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return ApiHandler


def build_http_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    app = App()
    return ThreadingHTTPServer((host, port), make_handler(app))


def run() -> None:
    server = build_http_server(host="127.0.0.1", port=8000)
    print("Server started on http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    run()
