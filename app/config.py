"""Settings from the environment and `.env`. Field names match `.env.example`.

Environment variables win over `.env`. Empty values count as unset, so a blank line in `.env`
leaves an optional field at its default. Nothing reads settings at import time: call
`get_settings()` where they are needed.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, Field, HttpUrl, SecretStr, TypeAdapter
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

_http_url = TypeAdapter(HttpUrl)


def _check_url(value: str) -> str:
    """Reject anything that is not an http(s) URL; keep the text, minus a trailing slash."""
    _http_url.validate_python(value)
    return value.rstrip("/")


Url = Annotated[str, AfterValidator(_check_url)]
Fraction = Annotated[float, Field(ge=0.0, le=1.0)]
Seconds = Annotated[float, Field(gt=0.0)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        frozen=True,
    )

    # Supabase (step 01). The backend uses only the URL and the secret key.
    supabase_url: Url
    supabase_secret_key: SecretStr
    supabase_publishable_key: SecretStr | None = None
    supabase_jwks_url: Url | None = None
    database_url: SecretStr | None = None
    home_id: UUID

    # Backend (D5, step 07)
    public_base_url: Url | None = None
    app_token: SecretStr | None = None

    # Gemini API (steps 04 and 05, D24). The Google SDK would also read GOOGLE_API_KEY by itself;
    # we pass it explicitly so tests and scripts see only these settings.
    google_api_key: SecretStr | None = None
    perception_model: str = "gemini-3.6-flash"

    # Roboflow (steps 04 and 05)
    roboflow_api_key: SecretStr | None = None
    roboflow_api_url: Url = "https://serverless.roboflow.com"
    roboflow_model_id: str | None = None

    # Perception thresholds and timeouts (step 05, D11, `.claude/rules/perception.md`)
    room_cut: Fraction = 0.6
    item_cut: Fraction = 0.5
    sam3_gate: Fraction = 0.5
    perception_timeout_s: Seconds = 10.0
    detector_timeout_s: Seconds = 5.0

    # Ingest worker (step 06, D10, D11)
    blur_cut: Annotated[float, Field(ge=0.0)] = 25.0
    duplicate_cut: Fraction = 0.95
    duplicate_refresh_s: Seconds = 10.0  # a still camera still sends a frame this often
    empty_look_every_s: Seconds = 30.0  # Gemini asked with no item in sight, for mark_absent
    vlm_in_flight: Annotated[int, Field(ge=1)] = 2  # more frames than this are dropped, not queued

    # Vapi (step 03)
    vapi_server_secret: SecretStr | None = None

    # LiveKit and Chert (step 10, optional). The LiveKit URL is wss://, so it is plain text.
    livekit_url: str | None = None
    livekit_api_key: SecretStr | None = None
    livekit_api_secret: SecretStr | None = None

    # Typesense (step 09, optional)
    typesense_host: str | None = None
    typesense_api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
