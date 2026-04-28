from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings

DATA_DIR = Path("/data") if Path("/data").exists() else Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    bitagent_graphql_url: str = "http://localhost:3333/graphql"
    bitagent_metrics_url: str = "http://localhost:3333/metrics"
    require_auth: bool = True
    dashboard_api_key: str = ""
    torznab_api_key: str = ""
    trust_npm_headers: bool = False
    trust_forwarded_user: bool = False
    sso_cookie_name: str = "bitagent_session"
    tmdb_api_key: str = ""
    log_level: str = "info"
    db_path: str = str(DATA_DIR / "bitagent-ui.db")
    host: str = "0.0.0.0"
    port: int = 8080

    model_config = {"env_prefix": "", "env_file": ".env", "extra": "ignore"}


settings = Settings()

MUTABLE_FIELDS: set[str] = {
    "bitagent_graphql_url",
    "bitagent_metrics_url",
    "tmdb_api_key",
    "log_level",
    "trust_npm_headers",
    "trust_forwarded_user",
    "sso_cookie_name",
    "torznab_api_key",
}
