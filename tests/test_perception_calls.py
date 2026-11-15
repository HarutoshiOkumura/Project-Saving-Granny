"""Retries, the Gemini call and the SAM 3 call, with fake clients. No network."""

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.perception import detector, retry, vlm
from app.perception.frame import Frame
from app.perception.schema import build_json_schema
from tests.perception_fakes import (
    CONTEXT,
    TABLE,
    FakeInteractions,
    StatusError,
    gemini_answer,
    rectangle,
    sam3_answer,
)

JPEG = b"\xff\xd8fake jpeg"


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Backoff sleeps are recorded, not slept."""
    slept: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        slept.append(seconds)

    monkeypatch.setattr(retry.asyncio, "sleep", fake_sleep)
    return slept


# --------------------------------------------------------------------------------------------
# with_retries
# --------------------------------------------------------------------------------------------


def flaky(*outcomes: object) -> tuple[Any, list[int]]:
    calls: list[int] = []

    async def call() -> object:
        calls.append(1)
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    return call, calls


def run(call: Any, **kwargs: Any) -> object:
    return asyncio.run(retry.with_retries(call, timeout_s=1.0, what="test", **kwargs))


def test_retries_429_5xx_and_network_errors_with_backoff(no_waiting: list[float]) -> None:
    call, calls = flaky(StatusError(429), StatusError(503), httpx.ConnectError("down"), "ok")

    assert run(call) == "ok"
    assert len(calls) == 4
    assert no_waiting == [1.0, 2.0, 4.0]


def test_gives_up_after_three_retries() -> None:
    call, calls = flaky(*[StatusError(500)] * 5)

    with pytest.raises(StatusError):
        run(call)
    assert len(calls) == 4


@pytest.mark.parametrize("error", [StatusError(400), StatusError(401), retry.GiveUp("status x")])
def test_does_not_retry_what_cannot_get_better(error: Exception) -> None:
    call, calls = flaky(error, "never")

    with pytest.raises(type(error)):
        run(call)
    assert len(calls) == 1


def test_each_attempt_has_a_hard_timeout() -> None:
    attempts: list[int] = []

    async def slow() -> str:
        attempts.append(1)
        if len(attempts) == 1:
            await asyncio.Event().wait()  # hangs forever
        return "ok"

    assert asyncio.run(retry.with_retries(slow, timeout_s=0.01, what="test")) == "ok"
    assert len(attempts) == 2


def test_retry_after_is_honoured_up_to_a_cap(no_waiting: list[float]) -> None:
    call, _ = flaky(StatusError(429, retry_after="7"), StatusError(429, retry_after="900"), "ok")

    run(call)

    assert no_waiting == [7.0, retry.RETRY_AFTER_CAP_S]


def test_sdk_connection_errors_count_as_retryable() -> None:
    class APIConnectionError(Exception):
        pass

    class APITimeoutError(APIConnectionError):
        pass

    assert retry.is_retryable(APITimeoutError())
    assert not retry.is_retryable(ValueError("bad JSON"))


# --------------------------------------------------------------------------------------------
# Gemini
# --------------------------------------------------------------------------------------------


@pytest.fixture
def gemini(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Install a fake Gemini client; returns a function that sets its answers."""

    def install(*answers: Any) -> FakeInteractions:
        fake = FakeInteractions(*answers)
        monkeypatch.setattr(vlm, "_get_client", lambda settings: fake.client)
        return fake

    return install


def test_look_sends_the_measured_request(gemini: Any) -> None:
    fake = gemini(gemini_answer())

    perception = asyncio.run(vlm.look(JPEG, CONTEXT))

    assert perception is not None and perception.items[0].landmark == TABLE
    (request,) = fake.requests
    assert request["model"] == "gemini-3.6-flash"
    assert request["store"] is False
    assert request["generation_config"] == {"thinking_level": "low"}
    assert request["response_format"] == {
        "type": "text",
        "mime_type": "application/json",
        "schema": build_json_schema(CONTEXT),
    }
    assert request["input"] == vlm.build_input(JPEG, vlm.build_prompt(CONTEXT))
    assert request["timeout"] == 10.0
    assert "temperature" not in json.dumps(request["generation_config"])


def test_look_retries_a_rate_limit_then_answers(gemini: Any) -> None:
    fake = gemini(StatusError(429), gemini_answer())

    assert asyncio.run(vlm.look(JPEG, CONTEXT)) is not None
    assert len(fake.requests) == 2


@pytest.mark.parametrize(
    "answer",
    [
        SimpleNamespace(status="incomplete", output_text='{"room": "b_school'),
        SimpleNamespace(status="failed", output_text=None),
        SimpleNamespace(status="completed", output_text=None),
        "not json",
        '{"room": "b_school_classroom"}',
        StatusError(400),
    ],
)
def test_look_skips_the_frame_without_retrying(gemini: Any, answer: Any) -> None:
    fake = gemini(answer, gemini_answer())

    assert asyncio.run(vlm.look(JPEG, CONTEXT)) is None
    assert len(fake.requests) == 1


def test_look_skips_the_frame_after_four_timeouts(gemini: Any) -> None:
    fake = gemini(*[TimeoutError()] * 4, gemini_answer())

    assert asyncio.run(vlm.look(JPEG, CONTEXT)) is None
    assert len(fake.requests) == 4


def test_look_keeps_names_inside_the_context(gemini: Any) -> None:
    gemini(gemini_answer([{"item": "wallet"}], room="kitchen"))

    perception = asyncio.run(vlm.look(JPEG, CONTEXT))

    assert perception is not None
    assert perception.room == "unknown"
    assert perception.items == []


def test_look_without_a_key_skips_the_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vlm, "_client", None)

    assert asyncio.run(vlm.look(JPEG, CONTEXT)) is None


def test_client_turns_the_sdk_retries_off(monkeypatch: pytest.MonkeyPatch) -> None:
    built: list[dict[str, Any]] = []
    monkeypatch.setattr(vlm.genai, "Client", lambda **kwargs: built.append(kwargs) or "client")
    monkeypatch.setattr(vlm, "_client", None)
    settings = SimpleNamespace(google_api_key=SimpleNamespace(get_secret_value=lambda: "k"))

    async def twice() -> tuple[object, object]:
        return vlm._get_client(settings), vlm._get_client(settings)

    assert asyncio.run(twice()) == ("client", "client")
    (kwargs,) = built  # one client per event loop
    assert kwargs["api_key"] == "k"
    assert kwargs["http_options"].retry_options.attempts == 1


# --------------------------------------------------------------------------------------------
# SAM 3
# --------------------------------------------------------------------------------------------

FRAME = Frame(JPEG, width=1000, height=2000)


@pytest.fixture
def roboflow(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Install a fake Roboflow server; returns a function that sets its replies."""

    def install(*replies: httpx.Response | Exception) -> list[httpx.Request]:
        seen: list[httpx.Request] = []
        queue = list(replies)

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            reply = queue.pop(0)
            if isinstance(reply, Exception):
                raise reply
            return reply

        client = httpx.AsyncClient(
            base_url="https://serverless.roboflow.com",
            headers={"Authorization": "Bearer rf_fake"},
            transport=httpx.MockTransport(handler),
        )
        monkeypatch.setattr(detector, "_get_client", lambda settings: client)
        return seen

    return install


def test_detect_sends_the_bakeoff_prompts_with_monitoring_off(roboflow: Any) -> None:
    seen = roboflow(httpx.Response(200, json=sam3_answer()))

    assert asyncio.run(detector.detect(FRAME)) == []
    (request,) = seen
    assert request.url == "https://serverless.roboflow.com/sam3/concept_segment"
    assert request.headers["authorization"] == "Bearer rf_fake"
    body = json.loads(request.content)
    assert body == {
        "image": {"type": "base64", "value": "/9hmYWtlIGpwZWc="},
        "prompts": [
            {"type": "text", "text": text}
            for text in [
                "green handbag",
                "eyeglasses",
                "bunch of keys",
                "wristwatch",
                "dark blue bottle",
            ]
        ],
        "output_prob_thresh": 0.1,
        "format": "polygon",
        "disable_model_monitoring": True,
    }


def test_detect_turns_mask_polygons_into_normalized_boxes(roboflow: Any) -> None:
    roboflow(
        httpx.Response(
            200,
            json=sam3_answer(
                (2, 0.8, rectangle(100, 200, 300, 600)),
                (3, 0.3, [[-50, 1900], [1200, 2100], [600, 1950]]),  # spills off the frame
                (4, 0.9, []),  # no points
            ),
        )
    )

    keys, watch = asyncio.run(detector.detect(FRAME))

    assert (keys.item, keys.prompt, keys.confidence) == ("keys", "bunch of keys", 0.8)
    assert keys.box == (100.0, 100.0, 300.0, 300.0)
    assert watch.item == "watch"
    assert watch.box == (950.0, 0.0, 1000.0, 1000.0)


def test_detect_retries_a_server_error(roboflow: Any) -> None:
    seen = roboflow(httpx.Response(502), httpx.Response(200, json=sam3_answer()))

    assert asyncio.run(detector.detect(FRAME)) == []
    assert len(seen) == 2


@pytest.mark.parametrize(
    "reply",
    [httpx.Response(401), httpx.Response(200, json={"error": "x"}), httpx.Response(200, text="?")],
)
def test_detect_raises_detector_error_without_retrying(roboflow: Any, reply: Any) -> None:
    seen = roboflow(reply, httpx.Response(200, json=sam3_answer()))

    with pytest.raises(detector.DetectorError):
        asyncio.run(detector.detect(FRAME))
    assert len(seen) == 1


def test_detect_raises_after_the_retries(roboflow: Any) -> None:
    seen = roboflow(*[httpx.ConnectError("down")] * 4)

    with pytest.raises(detector.DetectorError):
        asyncio.run(detector.detect(FRAME))
    assert len(seen) == 4


def test_detect_without_a_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(detector, "_client", None)

    with pytest.raises(detector.DetectorError, match="ROBOFLOW_API_KEY"):
        asyncio.run(detector.detect(FRAME))
