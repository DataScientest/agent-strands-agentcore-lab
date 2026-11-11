"""Timeout imposé par le parent : l'enquête ne peut pas repousser l'échéance."""

import argparse
import json
import subprocess
import sys


def invoke(incident: str, mode: str = "single", timeout: int = 360, tenant: str = "atelier-a") -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "incident_lab.worker", incident, "--mode", mode, "--tenant", tenant],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "TIMEOUT", "incident": incident, "mode": mode, "latency_s": timeout, "trace": []}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "ok": False,
            "error": "WORKER_FAILURE",
            "detail": proc.stderr[-500:],
            "incident": incident,
            "mode": mode,
            "trace": [],
        }


def main() -> None:
    p = argparse.ArgumentParser(description="Une enquête dans un processus séparé, bornée par un délai.")
    p.add_argument("incident")
    p.add_argument("--mode", choices=["single", "multi"], default="single")
    p.add_argument("--timeout", type=int, default=360)
    a = p.parse_args()
    result = invoke(a.incident, a.mode, a.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
