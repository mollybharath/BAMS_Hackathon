from __future__ import annotations
import io
from typing import Literal
import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from finguard.demo_data import demo_transactions
from finguard.agentic import run_agentic_investigation
from finguard.local_llm import local_model_enabled

app = FastAPI(title="FinGuard AI Local Investigation API", version="2.0.0", description="Local-first, auditable fraud/AML investigation demo. Synthetic data only.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
CASES: dict[str, dict] = {}

class ReviewRequest(BaseModel):
    decision: Literal["escalate", "approve_draft", "dismiss"]
    reviewer: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=3, max_length=1000)

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "FinGuard AI", "mode": "local-only", "local_llm_enabled": local_model_enabled(), "external_llm_calls": False}

@app.get("/api/demo")
def demo():
    df = demo_transactions()
    return {"transactions": df.to_dict(orient="records"), "count": len(df), "message": "Synthetic demo data. No external model calls."}

@app.post("/api/investigate")
def investigate(payload: dict):
    try:
        rows = payload.get("transactions")
        if not isinstance(rows, list) or not rows:
            raise ValueError("Provide a non-empty transactions array.")
        case_id = str(payload.get("case_id") or "CASE-DEMO-001")[:80]
        result = run_agentic_investigation(pd.DataFrame(rows), case_id=case_id)
        CASES[case_id] = result
        return result
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.post("/api/investigate/upload")
async def investigate_upload(file: UploadFile = File(...), case_id: str = "CASE-UPLOAD-001"):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file.")
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        result = run_agentic_investigation(df, case_id=case_id[:80])
        CASES[case_id[:80]] = result
        return result
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not investigate CSV: {exc}") from exc

@app.post("/api/cases/{case_id}/review")
def review(case_id: str, request: ReviewRequest):
    if case_id not in CASES:
        raise HTTPException(status_code=404, detail="Case not found. Run an investigation first.")
    case = CASES[case_id]
    case["human_decision"] = {"status": request.decision, "reviewer": request.reviewer.strip(), "reason": request.reason.strip(), "updated_at": pd.Timestamp.now(tz="UTC").isoformat()}
    case.setdefault("steps", []).append({"sequence": len(case["steps"])+1, "timestamp": case["human_decision"]["updated_at"], "agent": "Human Reviewer", "action": request.decision, "status": "recorded", "summary": request.reason.strip()})
    return {"case_id": case_id, "human_decision": case["human_decision"]}
