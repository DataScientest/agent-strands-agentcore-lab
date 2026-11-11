# Lab Strands + passerelle de la formation + Floci

Lab du parcours « Agents Strands et AgentCore ». Clonez-le dans un dossier `lab/`, d'où se lancent toutes les commandes de ce guide :

```bash
git clone https://github.com/DataScientest/agent-strands-agentcore-lab.git lab
cd lab
```

 Aucun compte AWS n'est nécessaire : AgentCore est émulé par Floci.

## Le modèle

Par défaut, l'agent appelle le modèle par la passerelle de la formation, compatible OpenAI. Le formateur fournit une clé, par apprenant ou pour la session :

```bash
export LLM_API_KEY=sk-...                                # clé fournie par le formateur
export LLM_BASE_URL=https://ai-gateway.liora.tech/v1      # valeur par défaut
export LLM_MODEL=anthropic/claude-haiku-5-5               # valeur par défaut
```

Une enquête prend alors quelques secondes. Sans `LLM_API_KEY`, l'agent prend un Ollama local (parcours Ollama, plus bas). Aucun repli de l'un vers l'autre : une passerelle injoignable donne une erreur, jamais un autre modèle. Ne mettez jamais la clé dans un fichier du lab.

Le modèle n'est pas garanti de réussir chaque incident ; les erreurs structurées et les traces font partie du TP. Les fichiers de `references/` conservent des enquêtes réelles faites avec `qwen2.5:3b` et `qwen2.5:7b`, dont des échecs : ils restent la base de plusieurs exercices.

## Parcours Python

```bash
uv sync --frozen
uv run python runner.py INC-001 > premiere-enquete.json
uv run python runner.py INC-002 --mode multi --timeout 360 > enquete-multi.json
uv run pytest -q
```

Docker ne sert ici qu'à Floci, pour le cours AgentCore.

## Parcours Docker Compose

```bash
docker compose pull floci
docker compose build agent
docker compose up -d floci agent
curl --fail http://127.0.0.1:18080/ping
```

Le service `agent` reçoit `LLM_API_KEY`, `LLM_BASE_URL` et `LLM_MODEL` de votre terminal. Ports hôte : agent 18080, Floci 14566. Le build utilise `uv.lock` ; Floci est épinglé par digest, et les images utilisées au contrôle sont listées dans `references/environment.json`.

Pour invoquer l'agent depuis son conteneur :

```bash
docker compose exec -T agent python - <<'PYTHON'
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
request = Request("http://127.0.0.1:8080/invocations",
                  data=json.dumps({"incident_id": "INC-001", "mode": "single"}).encode(),
                  headers={"Content-Type": "application/json"})
try:
    with urlopen(request, timeout=400) as response:
        print(response.status, response.read().decode())
except HTTPError as error:
    print(error.code, error.read().decode())  # conserver aussi une sortie d'enquête refusée
PYTHON
```

## Parcours Ollama, sans passerelle

Pour un poste assez puissant, sans clé. Ne lancez pas deux inférences simultanées : un essai CPU peut durer plusieurs minutes.

```bash
unset LLM_API_KEY
ollama pull qwen2.5:3b
uv run python runner.py INC-001 > premiere-enquete.json
```

Si nécessaire, démarrer `ollama serve` dans un autre terminal. `OLLAMA_HOST` vaut par défaut `http://127.0.0.1:11434` ; seul un hôte local est accepté, et un modèle relayé vers le cloud est refusé. `OLLAMA_MODEL` permet un autre modèle **local téléchargé et compatible outils**. La variante 3b de qwen2.5 possède une licence Qwen particulière ; vérifier les conditions d'utilisation pour l'organisation.

Avec Docker, Ollama est un service optionnel :

```bash
docker compose --profile ollama up -d floci ollama
docker compose exec -T ollama ollama pull qwen2.5:3b
docker compose up -d agent
```

Le service `ollama` est épinglé par digest et publié sur 11435 ; pour l'utiliser depuis le poste, définir `OLLAMA_HOST=http://127.0.0.1:11435`. Après préparation, `docker compose --profile ollama -f compose.yaml -f compose.offline.yaml up -d --force-recreate` passe au réseau interne : il bloque la sortie des conteneurs, donc aussi la passerelle. Avec le réseau interne seul, Docker peut ne plus publier les ports sur l'hôte : invoquez l'agent depuis son conteneur. Le réseau interne n'est pas un audit de sécurité de l'hôte Docker.

Changer de modèle, par la passerelle ou dans Ollama, exige de refaire les mesures, pas seulement de modifier son nom.

Pour exposer l'application Python directement :

```bash
uv run uvicorn server:app --host 127.0.0.1 --port 18080
```

Ne pas lancer cette commande si le conteneur agent utilise déjà le port 18080.

## API AgentCore émulée

Avec Floci démarré :

```bash
uv run python floci_lab.py
```

Le client utilise exclusivement `http://127.0.0.1:14566` par défaut, région eu-west-3, identifiants factices `test`. `FLOCI_ENDPOINT` accepte seulement localhost, 127.0.0.1 ou le service Compose `floci`. En réseau interne, lancer `docker compose exec -T -e FLOCI_ENDPOINT=http://floci:4566 agent python floci_lab.py`. Le script enregistre deux versions, crée un endpoint, invoque la simulation puis nettoie ses propres ressources. Le marqueur `SIMULATION_FLOCI_NO_AGENT_EXECUTED` ne vient pas de Strands. L'URI ECR et le rôle IAM de l'exercice sont fictifs; aucun push d'image ou déploiement AWS n'a lieu.

## Approbation et évaluation

```bash
uv run python actions.py
uv run python evaluate.py --mode single --split dev --repeats 1
uv run python evaluate.py --mode multi --split dev --repeats 1
```

`actions.py` manipule uniquement une proposition simulée en SQLite. L'approbation passe par le terminal de l'opérateur, jamais par les outils de l'agent. Une seconde exécution ne répète pas la transition locale.

Les évaluations écrivent progressivement dans `runs/`. Pour le benchmark complet, utiliser trois répétitions ou davantage en dehors de la séance. Le script classe INC-003 dans `--split holdout`. S’il a déjà été étudié dans le parcours, ce jeu ne constitue plus une évaluation à l’aveugle : réserver de nouveaux incidents pour une mesure indépendante. Les mêmes budgets globaux s'appliquent aux deux architectures. Un timeout reste un échec; ne pas le retirer des résultats.

`tokens` contient les compteurs disponibles du SDK ou `null`. Sur un échec, un comptage peut être partiel : ne pas l'interpréter comme une consommation complète. Les traces historiques antérieures à l'ajout du compteur n'ont pas cette clé. La qualité sémantique reste à annoter avec la grille du formateur; les contrôles de `evaluate.py` ne sont pas une mesure automatique de justesse métier.

## Fichiers à lire

| Fichier | Responsabilité |
| --- | --- |
| `incidents.json` | Corpus synthétique, INC-003 réservé au défi |
| `domain.py` | Périmètres, preuves consultées, budgets et schémas |
| `agent.py` | Prompt, outils, hook et workflow à deux spécialistes |
| `models.py` | Modèle : passerelle de la formation si `LLM_API_KEY` est défini, sinon Ollama local |
| `worker.py`, `runner.py` | Processus d'enquête et délai imposé par le parent |
| `server.py` | Sous-ensemble HTTP AgentCore local |
| `actions.py` | Proposition, approbation et exécution simulée idempotente |
| `floci_lab.py` | Registre et invocation AgentCore simulés |
| `evaluate.py`, `mesures.csv` | Résultats bruts et annotations humaines |
| `tests/` | Tests sans modèle, limites et contrat HTTP |
| `references/` | Sorties observées, y compris erreurs; aucune garantie de résultat |

## Dépannage

- Connexion refusée : vérifier le service et distinguer ports hôte et conteneur.
- Modèle absent : le télécharger pendant la préparation; le réseau interne empêche les téléchargements ultérieurs.
- `UNOBSERVED_CITATION` : le validateur a bloqué une référence non lue dans le périmètre du rapport. Lire la trace; ne pas supprimer le contrôle.
- Budget atteint : inspecter les répétitions, contrats et contexte avant d'augmenter le plafond.
- Timeout : vérifier la charge, utiliser les traces de référence ou un modèle local mieux adapté. Le parent termine le worker; une inférence déjà reçue par le modèle (Ollama ou passerelle) peut finir plus tard côté serveur.
- Image non disponible sur le matériel : préparer et tester les images et le modèle avant la formation. Une image locale x86 n'est pas un déploiement ARM64 AWS validé.

## Arrêt

```bash
docker compose -f compose.yaml -f compose.offline.yaml down
```

Cette commande conserve les poids dans le volume. Ne pas ajouter `-v` si tu souhaites conserver le téléchargement. Les sorties locales sont ignorées par git. Aucune ressource AWS n'est créée par le TP.

## Corrigé de l'amélioration du prompt

`system_hardened.txt` fournit un exemple plus explicite sur les métriques et l'abstention. Le prompt initial reste la baseline du cours. Pour changer une seule variable :

```bash
AGENT_VARIANT=hardened uv run python runner.py INC-001
AGENT_VARIANT=hardened uv run python evaluate.py --mode single --split dev --repeats 3
```

Les évaluations écrivent `runs/single-dev-baseline.json` ou `runs/single-dev-hardened.json`, selon la variante, afin de conserver les deux expériences. Les résultats dépendent du modèle : le corrigé est une hypothèse d'amélioration à évaluer, pas une garantie. La référence `single-inc001-7b.json` montre une exécution structurée avec qwen2.5:7b, mais contient encore une confusion sur une baisse de précision non mesurée; elle est à critiquer aussi. Le modèle 7b peut être choisi avec `OLLAMA_MODEL=qwen2.5:7b` après téléchargement; il exige davantage de mémoire.

Avec Docker, la même sélection s'applique à l'environnement du service agent :

```bash
AGENT_VARIANT=hardened docker compose -f compose.yaml -f compose.offline.yaml up -d agent
```

Pour changer de modèle dans Docker, définir `LLM_MODEL` (passerelle) ou, pour Ollama, télécharger d'abord ses poids puis définir `OLLAMA_MODEL`, lors du lancement du service agent. Après modification du code ou du fichier de prompt sur le poste, reconstruire l'image agent avant de recréer son conteneur. Les commandes `uv run` utilisent directement les fichiers du poste.
