from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_host: str
    app_port: int
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    db_sslmode: str

    @property
    def db_dsn(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?sslmode={self.db_sslmode}"
        )


def load_settings() -> Settings:
    return Settings(
        app_host=os.getenv("APP_HOST", "0.0.0.0"),
        app_port=int(os.getenv("APP_PORT", "8001")),
        db_host=os.getenv("DB_HOST", "db"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.getenv("DB_NAME", "sandwich"),
        db_user=os.getenv("DB_USER", "sandwich"),
        db_password=os.getenv("DB_PASSWORD", "sandwich"),
        db_sslmode=os.getenv("DB_SSLMODE", "disable"),
    )
