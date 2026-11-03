import pytest

from app.config import JWT_SECRET_ENV, load_settings


def test_load_settings_rejects_empty_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(JWT_SECRET_ENV, "")

    with pytest.raises(RuntimeError, match=f"{JWT_SECRET_ENV} must be set"):
        load_settings()


def test_load_settings_rejects_jwt_secret_shorter_than_32_utf8_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "x" * 31
    monkeypatch.setenv(JWT_SECRET_ENV, secret)

    with pytest.raises(RuntimeError, match="at least 32 UTF-8 bytes") as error:
        load_settings()

    assert secret not in str(error.value)


def test_load_settings_accepts_jwt_secret_of_exactly_32_utf8_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "x" * 32
    monkeypatch.setenv(JWT_SECRET_ENV, secret)

    assert load_settings().jwt_secret == secret


def test_load_settings_counts_utf8_bytes_for_jwt_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "é" * 16
    monkeypatch.setenv(JWT_SECRET_ENV, secret)

    assert len(secret) == 16
    assert len(secret.encode("utf-8")) == 32
    assert load_settings().jwt_secret == secret
