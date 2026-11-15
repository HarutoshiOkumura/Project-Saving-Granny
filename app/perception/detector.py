"""SAM 3 text prompts on Roboflow's serverless API: the only place that calls Roboflow (D3).

Inference only, on frames that never go into a Roboflow project (the workspace is public on the
Research plan). Every call sends `disable_model_monitoring: true` (D20). Request shape checked
against https://docs.roboflow.com/models/supported-models/sam3.md; the response fields
(`prompt_index`, `masks`, `confidence`) are not in that page and were read from step 04's
recorded answers.
"""

import asyncio
import base64
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from app.config import Settings, get_settings
from app.perception.frame import Frame
from app.perception.retry import GiveUp, describe, with_retries
from app.perception.schema import Detection, box_from_pixels

# One wording per demo item, the one that won the step 04 bake-off. Plain names box single keys
# instead of the bunch, and "reading glasses" misses the glasses. A new item needs a line here;
# until it has one, perceive() sends every frame to Gemini.
PROMPTS: dict[str, str] = {
    "bag": "green handbag",
    "glasses": "eyeglasses",
    "keys": "bunch of keys",
    "watch": "wristwatch",
    "water bottle": "dark blue bottle",
}
# Answers below this are not returned at all. The gate (settings.sam3_gate) is higher; weaker
# masks still help pick a tight crop box when they agree with Gemini's box.
FLOOR = 0.1

_client: tuple[asyncio.AbstractEventLoop, httpx.AsyncClient] | None = None


class DetectorError(Exception):
    """SAM 3 gave no usable answer after the retries."""


class _Prediction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    masks: list[list[list[float]]]  # polygons of [x, y] points, in pixels of the image sent
    confidence: float


class _PromptResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    prompt_index: int
    predictions: list[_Prediction]


class _Response(BaseModel):
    model_config = ConfigDict(extra="ignore")

    prompt_results: list[_PromptResult]


async def detect(frame: Frame) -> list[Detection]:
    """Every instance of every demo item's prompt at FLOOR or more. Raises DetectorError."""
    settings = get_settings()
    body = {
        "image": {"type": "base64", "value": base64.b64encode(frame.jpeg).decode()},
        "prompts": [{"type": "text", "text": text} for text in PROMPTS.values()],
        "output_prob_thresh": FLOOR,
        "format": "polygon",
        "disable_model_monitoring": True,
    }
    try:
        data = await with_retries(
            lambda: _post(body, settings),
            timeout_s=settings.detector_timeout_s,
            what="sam3",
        )
        return parse_response(data, frame.width, frame.height)
    except Exception as exc:
        raise DetectorError(describe(exc)) from exc


def parse_response(
    data: Any, width: int, height: int, prompts: dict[str, str] = PROMPTS
) -> list[Detection]:
    """Boxes from the mask polygons, normalized to 0..1000 and clipped to the frame. `prompts`
    is the item-to-wording map the request was built from, in the same order."""
    items = list(prompts)
    detections = []
    for result in _Response.model_validate(data).prompt_results:
        item = items[result.prompt_index]
        for prediction in result.predictions:
            points = [pt for polygon in prediction.masks for pt in polygon if len(pt) >= 2]
            if not points:
                continue
            xs = [min(max(pt[0], 0.0), width) for pt in points]
            ys = [min(max(pt[1], 0.0), height) for pt in points]
            if max(xs) <= min(xs) or max(ys) <= min(ys):
                continue
            detections.append(
                Detection(
                    item=item,
                    prompt=prompts[item],
                    confidence=prediction.confidence,
                    box=box_from_pixels(min(xs), min(ys), max(xs), max(ys), width, height),
                )
            )
    return detections


async def _post(body: dict[str, Any], settings: Settings) -> Any:
    response = await _get_client(settings).post("/sam3/concept_segment", json=body)
    response.raise_for_status()
    return response.json()


def _get_client(settings: Settings) -> httpx.AsyncClient:
    """One client per event loop, so connections are reused from frame to frame."""
    global _client
    loop = asyncio.get_running_loop()
    if _client is None or _client[0] is not loop:
        if settings.roboflow_api_key is None:
            raise GiveUp("ROBOFLOW_API_KEY is not set")
        client = httpx.AsyncClient(
            base_url=settings.roboflow_api_url,
            headers={"Authorization": f"Bearer {settings.roboflow_api_key.get_secret_value()}"},
            timeout=settings.detector_timeout_s,
        )
        _client = (loop, client)
    return _client[1]
