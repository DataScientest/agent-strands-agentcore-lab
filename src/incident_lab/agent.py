"""Agent Strands unique et décomposition contrôlée. Instances neuves par enquête."""

import json
from importlib.resources import files

from strands import Agent, tool
from strands.hooks import BeforeModelCallEvent, HookProvider, HookRegistry
from strands.models import Model

from incident_lab.config import settings
from incident_lab.contracts import Report
from incident_lab.domain import Budget, Investigation
from incident_lab.models import build_model

VARIANTS = {"baseline", "hardened"}


class Limits(HookProvider):
    def __init__(self, budget: Budget):
        self.budget = budget

    def register_hooks(self, registry: HookRegistry):
        registry.add_callback(BeforeModelCallEvent, self.before_model)

    def before_model(self, event):
        self.budget.model_call()


def system_prompt() -> str:
    variant = settings().agent_variant
    if variant not in VARIANTS:
        raise ValueError("AGENT_VARIANT doit être baseline ou hardened")
    return files("incident_lab").joinpath(f"prompts/{variant}.txt").read_text(encoding="utf-8")


def make_agent(state: Investigation, model: Model, extra: str = "") -> Agent:
    @tool
    def get_incident() -> dict:
        """Lit le résumé et les identifiants des preuves autorisées de l'incident courant."""
        return state.get_incident()

    @tool
    def read_evidence(evidence_id: str) -> dict:
        """Lit une preuve de l'incident courant avec source, date, unité et faits.

        Args:
            evidence_id: Un identifiant de cet incident renvoyé par get_incident.
        """
        return state.read_evidence(evidence_id)

    return Agent(
        model=model,
        system_prompt=system_prompt() + extra,
        tools=[get_incident, read_evidence],
        hooks=[Limits(state.budget)],
        callback_handler=None,
    )


def investigate(state: Investigation, mode: str = "single") -> Report:
    model = build_model()
    question = f"Enquête sur {state.incident_id}. Lis les preuves puis propose un diagnostic prudent."
    if mode == "multi":
        partials = []
        # Deux sous-agents séquentiels : la machine n'a besoin que d'un modèle en RAM.
        # Le workflow possède la décomposition; aucun handoff libre ou récursion.
        for role, kinds in [("données", {"data", "quality"}), ("déploiement", {"deployment"})]:
            child = Investigation(state.incident_id, state.tenant, state.budget, frozenset(kinds))
            agent = make_agent(child, model, f" Tu es spécialiste {role}; reste dans ton périmètre.")
            result = agent(question, structured_output_model=Report)
            collect_usage(state.budget, result)
            report = child.validate_report(result.structured_output)
            state.observed.update(child.observed)
            partials.append(report.model_dump())
        # Synthèse sans outil : aucune nouvelle autorisation n'est créée par les spécialistes.
        supervisor = Agent(
            model=model,
            system_prompt=system_prompt() + " Synthétise ces rapports. Préserve leurs désaccords et limites.",
            hooks=[Limits(state.budget)],
            callback_handler=None,
        )
        result = supervisor(json.dumps(partials, ensure_ascii=False), structured_output_model=Report)
    else:
        result = make_agent(state, model)(question, structured_output_model=Report)
    collect_usage(state.budget, result)
    return state.validate_report(result.structured_output)


def collect_usage(budget: Budget, result) -> None:
    usage = result.metrics.accumulated_usage
    if usage.get("totalTokens", 0) > 0:
        old = budget.usage or {}
        budget.usage = {k: old.get(k, 0) + usage.get(k, 0) for k in ("inputTokens", "outputTokens", "totalTokens")}
