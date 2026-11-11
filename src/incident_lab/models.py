"""Le modèle du lab : la passerelle de la formation (compatible OpenAI) si LLM_API_KEY est défini, sinon un
Ollama local. Aucun repli de l'un vers l'autre : une passerelle en panne donne une erreur, jamais un autre
modèle."""

from urllib.parse import urlparse

import httpx
from strands.models import Model
from strands.models.ollama import OllamaModel

from incident_lab.config import Settings, settings

LOCAL_HOSTS = {"127.0.0.1", "localhost"}


def gateway_model(s: Settings) -> Model:
    url = urlparse(s.llm_base_url)
    if url.scheme != "https" and url.hostname not in LOCAL_HOSTS:
        raise ValueError("La passerelle doit être en https")
    from strands.models.openai import OpenAIModel

    # Sans température : les modèles récents la refusent. 4000 jetons : la synthèse du mode multi.
    return OpenAIModel(
        client_args={"api_key": s.llm_api_key.get_secret_value(), "base_url": s.llm_base_url},
        model_id=s.llm_model,
        params={"max_tokens": 4000},
    )


def local_model(s: Settings) -> Model:
    if urlparse(s.ollama_host).hostname not in LOCAL_HOSTS | {"ollama"}:
        raise ValueError("Le TP accepte seulement Ollama local")
    # Un serveur local peut proposer un modèle cloud : contrôler les métadonnées.
    tags = httpx.get(s.ollama_host + "/api/tags", timeout=10).raise_for_status().json()["models"]
    match = next((m for m in tags if m["name"] == s.ollama_model), None)
    if match is None or match.get("remote_host") or match.get("remote_model") or "cloud" in s.ollama_model:
        raise ValueError("Télécharger un modèle local; les modèles cloud sont refusés")
    return OllamaModel(
        host=s.ollama_host, model_id=s.ollama_model, temperature=0, max_tokens=1500, options={"num_ctx": 8192}
    )


def build_model(s: Settings | None = None) -> Model:
    s = s or settings()
    return gateway_model(s) if s.uses_gateway else local_model(s)


def model_name(s: Settings | None = None) -> str:
    s = s or settings()
    return s.llm_model if s.uses_gateway else s.ollama_model
