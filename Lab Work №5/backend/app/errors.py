from __future__ import annotations


class ApiError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 404)


class ValidationError(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 400)


class ConflictError(ApiError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 409)
