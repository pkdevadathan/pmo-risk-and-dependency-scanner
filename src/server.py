"""FastAPI entrypoint for Vercel — same analysis engine as Streamlit, HTTP + static UI."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline import analyze_documents
from taxonomy import RISK_CATEGORIES

app = FastAPI(title="PMO Risk & Dependency Scanner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScanBody(BaseModel):
    bundle: str = Field(..., min_length=1, max_length=200_000)
    model: str = Field(default="gpt-4o-mini")


@app.get("/", response_model=None)
async def serve_ui() -> FileResponse | JSONResponse:
    index = ROOT / "public" / "index.html"
    if not index.is_file():
        return JSONResponse({"ok": True, "docs": "/docs", "health": "/api/health"})
    return FileResponse(index, media_type="text/html; charset=utf-8")


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/taxonomy")
def taxonomy() -> dict[str, list[str]]:
    return {"risk_categories": RISK_CATEGORIES}


@app.get("/api/samples")
def samples() -> dict[str, list[dict[str, str]]]:
    base = ROOT / "sample_docs"
    files: list[dict[str, str]] = []
    try:
        for p in sorted(base.glob("*.txt")):
            files.append({"name": p.name, "content": p.read_text(encoding="utf-8")})
    except OSError:
        pass
    return {"files": files}


@app.post("/api/scan")
def scan(body: ScanBody) -> dict[str, object]:
    try:
        result, mode = analyze_documents(body.bundle, model=body.model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"mode": mode, "result": result.model_dump()}
