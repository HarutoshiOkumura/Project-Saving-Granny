"""FastAPI app and routes only. Handlers stay thin: parse, call one function, return."""

from fastapi import FastAPI

app = FastAPI(title="Save It")


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
