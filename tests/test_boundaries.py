import pytest

from incident_lab.actions import approve, connect, execute, propose
from incident_lab.contracts import Finding, Report
from incident_lab.domain import Budget, BudgetExceeded, Investigation


def report(incident="INC-001", ids=None):
    return Report(
        incident_id=incident,
        status="hypothesis",
        findings=[Finding(hypothesis="Dérive possible", evidence_ids=ids or ["E-101"], limitation="Sans labels")],
        unknowns=["Qualité réelle"],
        proposed_action="Inspecter caméra",
        requires_human_approval=True,
    )


def test_cross_tenant_and_cross_incident_are_not_found():
    assert Investigation("INC-005").get_incident()["error"] == "NOT_FOUND"
    assert Investigation("INC-001").read_evidence("E-501")["error"] == "NOT_FOUND"


def test_new_sessions_do_not_share_evidence_or_retries():
    first, second = Investigation("INC-001"), Investigation("INC-001")
    first.read_evidence("E-101")
    assert not second.observed and not second.attempts and not second.budget.events


def test_unread_citations_and_wrong_incident_are_rejected():
    state = Investigation("INC-001")
    with pytest.raises(ValueError, match="UNOBSERVED_CITATION"):
        state.validate_report(report())
    state.read_evidence("E-101")
    assert state.validate_report(report()).incident_id == "INC-001"
    with pytest.raises(ValueError, match="INCIDENT_MISMATCH"):
        state.validate_report(report("INC-002"))


def test_retryable_error_does_not_count_as_evidence():
    state = Investigation("INC-006")
    assert state.read_evidence("E-601")["retryable"] is True
    assert not state.observed
    assert state.read_evidence("E-601")["id"] == "E-601"
    assert state.observed == {"E-601"}


def test_specialists_share_global_budget_but_not_permissions():
    budget = Budget(max_tools=1, max_models=1)
    a = Investigation("INC-001", budget=budget, allowed_kinds=frozenset({"data"}))
    assert a.read_evidence("E-102")["error"] == "NOT_FOUND"
    b = Investigation("INC-001", budget=budget)
    with pytest.raises(BudgetExceeded):
        b.get_incident()
    budget.model_call()
    with pytest.raises(BudgetExceeded):
        budget.model_call()


def test_approval_is_bound_to_content_and_execution_is_idempotent(tmp_path):
    db = connect(tmp_path / "actions.sqlite3")
    action = {"kind": "inspect_camera", "incident_id": "INC-001"}
    pid = propose(db, action)
    with pytest.raises(PermissionError):
        execute(db, pid)
    with pytest.raises(ValueError, match="STALE_APPROVAL"):
        approve(db, pid, {**action, "incident_id": "INC-002"})
    approve(db, pid, action)
    assert execute(db, pid)["result"] == "SIMULATED_ACTION"
    assert execute(db, pid)["result"] == "ALREADY_EXECUTED"
    db.close()


def test_report_cannot_disable_approval():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Report(**{**report().model_dump(), "requires_human_approval": False})


def test_injection_is_only_data_and_no_action_tool_is_exposed():
    from unittest.mock import Mock

    from strands.models import Model

    from incident_lab.agent import make_agent

    state = Investigation("INC-004")
    assert "ignore" in state.read_evidence("E-401")["facts"]
    agent = make_agent(state, Mock(spec=Model))
    assert set(agent.tool_names) == {"get_incident", "read_evidence"}


def test_gateway_must_be_https_and_never_falls_back(monkeypatch):
    from strands.models.openai import OpenAIModel

    from incident_lab.models import build_model

    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_BASE_URL", "http://example.com/v1")
    with pytest.raises(ValueError, match="https"):
        build_model()
    monkeypatch.setenv("LLM_BASE_URL", "https://gateway.example/v1")
    assert isinstance(build_model(), OpenAIModel)


def test_remote_ollama_host_and_remote_model_are_refused(monkeypatch):
    from incident_lab.models import build_model

    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("OLLAMA_HOST", "https://example.com")
    with pytest.raises(ValueError, match="local"):
        build_model()
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:3b")

    class Response:
        def raise_for_status(self):
            return self

        def json(self):
            return {"models": [{"name": "qwen2.5:3b", "remote_host": "https://example.com"}]}

    monkeypatch.setattr("incident_lab.models.httpx.get", lambda *args, **kwargs: Response())
    with pytest.raises(ValueError, match="cloud"):
        build_model()


def test_floci_client_cannot_fall_back_to_aws(monkeypatch):
    from incident_lab.floci import client

    monkeypatch.setenv("FLOCI_ENDPOINT", "https://bedrock-agentcore.eu-west-3.amazonaws.com")
    with pytest.raises(ValueError, match="local"):
        client("bedrock-agentcore")


def test_settings_come_from_the_environment_and_the_key_stays_secret(monkeypatch):
    from incident_lab.config import settings
    from incident_lab.models import model_name

    monkeypatch.setenv("LLM_API_KEY", "sk-secret")
    monkeypatch.setenv("LLM_MODEL", "un-modele")
    assert settings().uses_gateway and model_name() == "un-modele"
    assert "sk-secret" not in repr(settings())
    monkeypatch.setenv("LLM_API_KEY", "")
    assert model_name() == "qwen2.5:3b"


def test_an_unknown_prompt_variant_is_refused(monkeypatch):
    from incident_lab.agent import system_prompt

    monkeypatch.setenv("AGENT_VARIANT", "hardened")
    assert "PREDITS" in system_prompt()
    monkeypatch.setenv("AGENT_VARIANT", "autre")
    with pytest.raises(ValueError, match="baseline ou hardened"):
        system_prompt()
