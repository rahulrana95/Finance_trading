import pytest

from fintrade.core.redaction import (
    REDACTED,
    is_sensitive_key,
    redact_mapping,
    redact_processor,
    redact_value,
)

# Built at runtime so secret scanners do not flag a fake token.
JWT = ".".join(["eyJ" + "hbGciOi", "eyJ" + "zdWIi", "c2lnbmF0dXJl"])


@pytest.mark.parametrize(
    "key",
    [
        "access_token",
        "DHAN_ACCESS_TOKEN",
        "client_secret",
        "Password",
        "api_key",
        "Authorization",
        "set-cookie",
        "dhan_client_id",
        "totp_seed",
        "pan",
        "user_PAN",
        "account_number",
    ],
)
def test_sensitive_keys_detected(key: str) -> None:
    assert is_sensitive_key(key)


@pytest.mark.parametrize(
    "key", ["strike", "expiry", "event", "position_id", "lots", "span_id", "company", "expand"]
)
def test_normal_keys_not_flagged(key: str) -> None:
    assert not is_sensitive_key(key)


def test_sensitive_key_values_hidden_whatever_their_type() -> None:
    result = redact_mapping({"access_token": "abc", "password": 12345, "strike": 25800})
    assert result == {"access_token": REDACTED, "password": REDACTED, "strike": 25800}


def test_bearer_and_jwt_values_hidden_under_innocent_keys() -> None:
    result = redact_mapping({"note": "header Bearer abc.def", "payload": f"jwt={JWT} end"})
    assert result == {"note": f"header {REDACTED}", "payload": f"jwt={REDACTED} end"}


def test_nested_structures_redacted() -> None:
    data = {"request": {"headers": {"Authorization": "x"}, "args": [JWT, ("ok", JWT)]}}
    assert redact_mapping(data) == {
        "request": {"headers": {"Authorization": REDACTED}, "args": [REDACTED, ("ok", REDACTED)]}
    }


def test_plain_values_untouched() -> None:
    assert redact_value("NIFTY 25800 CE") == "NIFTY 25800 CE"
    assert redact_value(42) == 42
    assert redact_value(None) is None


def test_input_not_mutated() -> None:
    data = {"token": "abc"}
    redact_mapping(data)
    assert data == {"token": "abc"}


def test_processor_redacts_event_dict() -> None:
    out = redact_processor(None, "info", {"event": "login", "access_token": "abc"})
    assert out == {"event": "login", "access_token": REDACTED}
