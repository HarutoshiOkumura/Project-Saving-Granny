from uuid import UUID

import pytest
from pydantic import SecretStr, ValidationError

from app.config import ENV_FILE, Settings, get_settings


def test_reads_fake_environment_only() -> None:
    settings = get_settings()

    assert settings.supabase_url == "https://fake-project.supabase.co"
    assert settings.home_id == UUID("11111111-1111-1111-1111-111111111111")
    # Set in the real .env on a dev machine; must stay unset in tests.
    assert settings.supabase_publishable_key is None
    assert Settings.model_config["env_file"] is None
    assert ENV_FILE.name == ".env"


def test_keys_are_secret() -> None:
    settings = get_settings()

    assert isinstance(settings.supabase_secret_key, SecretStr)
    assert "sb_secret_fake" not in repr(settings)
    assert settings.supabase_secret_key.get_secret_value() == "sb_secret_fake"


def test_later_services_are_optional_with_defaults() -> None:
    settings = get_settings()

    assert settings.google_api_key is None
    assert settings.public_base_url is None
    assert settings.perception_model == "gemini-3.6-flash"
    assert settings.roboflow_api_url == "https://serverless.roboflow.com"


def test_empty_value_counts_as_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    monkeypatch.setenv("PERCEPTION_MODEL", "")

    settings = Settings()

    assert settings.google_api_key is None
    assert settings.perception_model == "gemini-3.6-flash"


def test_url_loses_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://save-it.example.com/")

    assert Settings().public_base_url == "https://save-it.example.com"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("HOME_ID", "not-a-uuid"),
        ("SUPABASE_URL", "fake-project.supabase.co"),
        ("PUBLIC_BASE_URL", "ftp://save-it.example.com"),
    ],
)
def test_bad_values_fail_fast(monkeypatch: pytest.MonkeyPatch, name: str, value: str) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(ValidationError):
        Settings()


def test_required_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_SECRET_KEY")

    with pytest.raises(ValidationError, match="supabase_secret_key"):
        Settings()
