from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from order_api.errors import ApiError, ValidationError
from order_api.models import Customer, FulfillmentType, NotificationRecord, Order
from order_api.repositories import (
    InMemoryCustomerRepository,
    InMemoryNotificationRepository,
    InMemoryOrderRepository,
)
from order_api.service import CreateOrderPayload, OrderApiService


class App:
    def __init__(self) -> None:
        self.service = OrderApiService(
            customers=InMemoryCustomerRepository(),
            orders=InMemoryOrderRepository(),
            notifications=InMemoryNotificationRepository(),
        )


def customer_to_dict(customer: Customer) -> dict[str, object]:
    return {
        "customer_id": customer.customer_id,
        "name": customer.name,
        "email": customer.email,
        "push_token": customer.push_token,
        "push_enabled": customer.preference.push_enabled,
        "email_enabled": customer.preference.email_enabled,
    }


def order_to_dict(order: Order) -> dict[str, object]:
    return {
        "order_id": order.order_id,
        "customer_id": order.customer_id,
        "store_id": order.store_id,
        "fulfillment": order.fulfillment.value,
        "status": order.status.value,
        "history": [item.value for item in order.history],
        "total_amount": order.total_amount,
        "updated_at": order.updated_at.isoformat(),
    }


def notification_to_dict(notification: NotificationRecord) -> dict[str, object]:
    return {
        "notification_id": notification.notification_id,
        "order_id": notification.order_id,
        "channel": notification.channel,
        "recipient": notification.recipient,
        "message": notification.message,
        "created_at": notification.created_at.isoformat(),
    }


def make_handler(app: App) -> type[BaseHTTPRequestHandler]:
    class ApiHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = _split_path(parsed.path)
            query = parse_qs(parsed.query)

            try:
                if path == ["api", "v1", "health"]:
                    self._send_json({"status": "ok"}, HTTPStatus.OK)
                    return

                if path == ["api", "v1", "orders"]:
                    status = _get_first(query, "status")
                    customer_id = _get_first(query, "customer_id")
                    orders = app.service.list_orders(status=status, customer_id=customer_id)
                    self._send_json({"items": [order_to_dict(item) for item in orders]}, HTTPStatus.OK)
                    return

                if len(path) == 4 and path[:3] == ["api", "v1", "orders"]:
                    order = app.service.get_order(path[3])
                    self._send_json(order_to_dict(order), HTTPStatus.OK)
                    return

                if len(path) == 5 and path[:3] == ["api", "v1", "orders"] and path[4] == "notifications":
                    items = app.service.list_notifications(path[3])
                    self._send_json(
                        {"items": [notification_to_dict(item) for item in items]},
                        HTTPStatus.OK,
                    )
                    return

                if len(path) == 4 and path[:3] == ["api", "v1", "customers"]:
                    customer = app.service.get_customer(path[3])
                    self._send_json(customer_to_dict(customer), HTTPStatus.OK)
                    return

                self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            except ApiError as exc:
                self._send_json({"error": exc.message}, exc.status_code)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = _split_path(parsed.path)
            body = self._read_json_body()

            try:
                if path == ["api", "v1", "customers"]:
                    customer = app.service.create_customer(body)
                    self._send_json(customer_to_dict(customer), HTTPStatus.CREATED)
                    return

                if path == ["api", "v1", "orders"]:
                    payload = CreateOrderPayload(
                        order_id=str(body["order_id"]),
                        customer_id=str(body["customer_id"]),
                        store_id=str(body["store_id"]),
                        fulfillment=_parse_fulfillment(body.get("fulfillment", "pickup")),
                        total_amount=float(body.get("total_amount", 0.0)),
                    )
                    order = app.service.create_order(payload)
                    self._send_json(order_to_dict(order), HTTPStatus.CREATED)
                    return

                if len(path) == 5 and path[:3] == ["api", "v1", "orders"] and path[4] == "status":
                    if "status" not in body:
                        raise ValidationError("Поле status обязательно.")
                    order = app.service.change_order_status(path[3], str(body["status"]))
                    self._send_json(order_to_dict(order), HTTPStatus.OK)
                    return

                self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            except KeyError as exc:
                self._send_json({"error": f"missing_field:{exc.args[0]}"}, HTTPStatus.BAD_REQUEST)
            except ApiError as exc:
                self._send_json({"error": exc.message}, exc.status_code)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

        def do_PUT(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = _split_path(parsed.path)
            body = self._read_json_body()

            try:
                if len(path) == 4 and path[:3] == ["api", "v1", "orders"]:
                    order = app.service.update_order(path[3], body)
                    self._send_json(order_to_dict(order), HTTPStatus.OK)
                    return
                self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            except ApiError as exc:
                self._send_json({"error": exc.message}, exc.status_code)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = _split_path(parsed.path)

            try:
                if len(path) == 4 and path[:3] == ["api", "v1", "orders"]:
                    app.service.delete_order(path[3])
                    self.send_response(int(HTTPStatus.NO_CONTENT))
                    self.end_headers()
                    return
                self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            except ApiError as exc:
                self._send_json({"error": exc.message}, exc.status_code)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def _read_json_body(self) -> dict[str, object]:
            size = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(size) if size else b"{}"
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValidationError("JSON body должен быть объектом.")
            return data

        def _send_json(self, payload: dict[str, object], status: int | HTTPStatus) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(int(status))
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ApiHandler


def _split_path(path: str) -> list[str]:
    return [part for part in path.split("/") if part]


def _get_first(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    return values[0]


def _parse_fulfillment(value: object) -> FulfillmentType:
    text = str(value)
    if text not in {"pickup", "delivery"}:
        raise ValidationError("Поле fulfillment должно быть pickup или delivery.")
    return FulfillmentType(text)


def build_server(host: str = "127.0.0.1", port: int = 8001) -> ThreadingHTTPServer:
    app = App()
    return ThreadingHTTPServer((host, port), make_handler(app))


def run() -> None:
    server = build_server(host="127.0.0.1", port=8001)
    print("REST API started on http://127.0.0.1:8001/api/v1")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    run()
