"""Une enquête par processus; stdout contient uniquement le résultat JSON."""
import argparse
import json
import os
import sys
import time
from agent import investigate; from models import model_name
from domain import Investigation


def run(incident, mode, tenant="atelier-a", models=12, tools=16):
    state = Investigation(incident, tenant)
    state.budget.max_models, state.budget.max_tools = models, tools
    started = time.monotonic()
    try:
        report = investigate(state, mode)
        result = {"ok": True, "report": report.model_dump()}
    except Exception as exc:
        result = {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:500]}
    return {**result, "incident": incident, "mode": mode,
            "variant": os.getenv("AGENT_VARIANT", "baseline"),
            "model": model_name(),
            "model_calls": state.budget.models, "tool_calls": state.budget.tools,
            "tokens": getattr(state.budget, "usage", None),
            "latency_s": round(time.monotonic() - started, 3), "trace": state.budget.events}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("incident")
    p.add_argument("--mode", choices=["single", "multi"], default="single")
    p.add_argument("--tenant", default="atelier-a")
    p.add_argument("--models", type=int, default=12)
    p.add_argument("--tools", type=int, default=16)
    a = p.parse_args()
    result = run(a.incident, a.mode, a.tenant, a.models, a.tools)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)
