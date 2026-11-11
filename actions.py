"""Approbation hors agent, liée au contenu exact; SQLite garantit l'idempotence locale."""
import hashlib
import json
import sqlite3


def digest(action):
    return hashlib.sha256(json.dumps(action, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def connect(path):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS proposals (id TEXT PRIMARY KEY, payload TEXT, approved INTEGER DEFAULT 0, executed INTEGER DEFAULT 0)")
    return db


def propose(db, action):
    if action.get("kind") not in {"request_labels", "inspect_camera", "compare_versions"}:
        raise ValueError("ACTION_NOT_ALLOWED")
    pid = digest(action)
    with db:
        db.execute("INSERT OR IGNORE INTO proposals(id, payload) VALUES (?, ?)", (pid, json.dumps(action, sort_keys=True)))
    return pid


def approve(db, pid, reviewed_action):
    if digest(reviewed_action) != pid:
        raise ValueError("STALE_APPROVAL")
    with db:
        if not db.execute("UPDATE proposals SET approved=1 WHERE id=?", (pid,)).rowcount:
            raise ValueError("UNKNOWN_PROPOSAL")


def execute(db, pid):
    with db:
        row = db.execute("SELECT approved, executed FROM proposals WHERE id=?", (pid,)).fetchone()
        if row is None or not row[0]:
            raise PermissionError("APPROVAL_REQUIRED")
        changed = db.execute("UPDATE proposals SET executed=1 WHERE id=? AND executed=0", (pid,)).rowcount
    return {"id": pid, "result": "SIMULATED_ACTION" if changed else "ALREADY_EXECUTED"}


if __name__ == "__main__":
    db = connect("actions.sqlite3")
    action = {"incident_id": "INC-001", "kind": "inspect_camera"}
    pid = propose(db, action)
    print("Proposition exacte :", json.dumps(action), "empreinte :", pid)
    # Ce terminal représente l'opérateur authentifié; il n'est pas un outil de l'agent.
    if input("Saisir APPROUVER pour cette action simulée : ") == "APPROUVER":
        approve(db, pid, action)
        print(execute(db, pid))
        print(execute(db, pid))
