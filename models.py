"""Modèle du lab : la passerelle de la formation (compatible OpenAI) si LLM_API_KEY est défini.
Sans clé, agent.local_model prend un Ollama local. Aucun repli de l'un vers l'autre : une passerelle en
panne donne une erreur, jamais un autre modèle."""
import os
from urllib.parse import urlparse
from strands.models.ollama import OllamaModel

GATEWAY = "https://ai-gateway.liora.tech/v1"
DEFAULT = "anthropic/claude-haiku-5-5"


def gateway_model():
    key = os.getenv("LLM_API_KEY", "")
    if not key:
        return None
    url = os.getenv("LLM_BASE_URL", GATEWAY)
    if urlparse(url).scheme != "https" and urlparse(url).hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("La passerelle doit être en https")
    from strands.models.openai import OpenAIModel
    # Sans température : les modèles récents la refusent. 4000 jetons : la synthèse du mode multi.
    return OpenAIModel(client_args={"api_key": key, "base_url": url},
                       model_id=os.getenv("LLM_MODEL", DEFAULT), params={"max_tokens": 4000})


def model_name():
    if os.getenv("LLM_API_KEY"):
        return os.getenv("LLM_MODEL", DEFAULT)
    return os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
