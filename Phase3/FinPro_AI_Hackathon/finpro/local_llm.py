"""Optional Ollama adapter. It only calls a local host and never a cloud model API.

Set FINPRO_LOCAL_MODEL to enable it, for example `llama3.2`. Core scoring,
evidence IDs, and validation always remain deterministic Python logic.
"""
from __future__ import annotations
import json
import os
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def local_model_enabled() -> bool:
    return bool(os.getenv("FINPRO_LOCAL_MODEL", "").strip())


def generate_local_summary(case_id: str, score: int, priority: str, findings: list[dict], missing_context: list[str], timeout: float = 8.0) -> dict:
    model = os.getenv("FINPRO_LOCAL_MODEL", "").strip()
    if not model:
        return {"enabled": False, "status": "disabled", "summary": None, "model": None}
    base_url = os.getenv("FINPRO_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    payload = {
        "model": model,
        "stream": False,
        "prompt": (
            "You are a cautious financial-crime investigation writing assistant. Summarize only the supplied evidence. "
            "Do not infer guilt or claim a crime occurred. Clearly distinguish observed patterns from hypotheses, "
            "mention uncertainty and missing context, and recommend human verification. Keep under 120 words.\n"
            + json.dumps({"case_id": case_id, "illustrative_score": score, "priority": priority,
                          "findings": [{"finding": f.get("finding"), "interpretation": f.get("interpretation"), "evidence_ids": f.get("evidence_ids", [])} for f in findings],
                          "missing_context": missing_context}, ensure_ascii=False)
        ),
        "options": {"temperature": 0.1}
    }
    req = Request(base_url + "/api/generate", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        text = str(data.get("response", "")).strip()
        if not text:
            return {"enabled": True, "status": "empty_response", "summary": None, "model": model}
        return {"enabled": True, "status": "complete", "summary": text, "model": model}
    except (URLError, HTTPError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {"enabled": True, "status": "fallback", "summary": None, "model": model,
                "message": f"Local model unavailable; deterministic report retained ({type(exc).__name__})."}
