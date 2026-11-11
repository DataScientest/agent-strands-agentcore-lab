"""Réglages du lab, lus dans l'environnement (ou un fichier `.env` jamais versionné) à chaque appel.

Les contrôles de sécurité (https, hôtes locaux) restent au point d'usage, dans `models.py` et `floci.py` :
une valeur mal réglée n'empêche que ce qui s'en sert."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

GATEWAY = "https://ai-gateway.liora.tech/v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_api_key: SecretStr = SecretStr("")  # clé de la passerelle de la formation ; vide : Ollama local
    llm_base_url: str = GATEWAY
    llm_model: str = "anthropic/claude-haiku-5-5"
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    agent_variant: str = "baseline"  # baseline ou hardened : le prompt système
    floci_endpoint: str = "http://127.0.0.1:14566"

    @property
    def uses_gateway(self) -> bool:
        return bool(self.llm_api_key.get_secret_value())


def settings() -> Settings:
    return Settings()
