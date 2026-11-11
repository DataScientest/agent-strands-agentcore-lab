"""Une enquête par processus; stdout contient uniquement le résultat JSON."""

import argparse
import json
import sys
import time

from incident_lab.agent import investigate
from incident_lab.config import settings
from incident_lab.domain import Investigation
from incident_lab.models import model_name


def run(incident: str, mode: str, tenant: str = "atelier-a", models: int = 12, tools: int = 16) -> dict:
    state = Investigation(incident, tenant)
    state.budget.max_models, state.budget.max_tools = models, tools
    started = time.monotonic()
    try:
        report = investigate(state, mode)
        result = {"ok": True, "report": report.model_dump()}
    except Exception as exc:
        result = {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:500]}
    return {
        **result,
        "incident": incident,
        "mode": mode,
        "variant": settings().agent_variant,
        "model": model_name(),
        "model_calls": state.budget.models,
        "tool_calls": state.budget.tools,
        "tokens": state.budget.usage,
        "latency_s": round(time.monotonic() - started, 3),
        "trace": state.budget.events,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Une enquête, dans ce processus.")
    p.add_argument("incident")
    p.add_argument("--mode", choices=["single", "multi"], default="single")
    p.add_argument("--tenant", default="atelier-a")
    p.add_argument("--models", type=int, default=12)
    p.add_argument("--tools", type=int, default=16)
    a = p.parse_args()
    result = run(a.incident, a.mode, a.tenant, a.models, a.tools)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
