"""
Définition des outils disponibles pour l'agent.

Chaque outil a :
- un schéma JSON (pour dire au modèle comment l'utiliser)
- une fonction Python qui l'exécute réellement

C'est la partie qui rend l'agent "agentique" : il peut agir sur le monde,
pas juste générer du texte.
"""

import os

NOTES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes")
os.makedirs(NOTES_DIR, exist_ok=True)


# --- Schémas des outils (ce que le modèle voit) ---

TOOLS = [
    {
        "name": "list_notes",
        "description": "Liste tous les fichiers de notes disponibles dans le dossier notes.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "read_note",
        "description": "Lit le contenu d'une note existante.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Nom du fichier à lire, par exemple 'idees.txt'",
                }
            },
            "required": ["filename"],
        },
    },
    {
        "name": "write_note",
        "description": "Crée ou remplace une note avec le contenu donné.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Nom du fichier à écrire, par exemple 'idees.txt'",
                },
                "content": {
                    "type": "string",
                    "description": "Contenu à écrire dans le fichier",
                },
            },
            "required": ["filename", "content"],
        },
    },
]


# --- Implémentation réelle des outils ---

def _safe_path(filename: str) -> str:
    """Empêche de sortir du dossier notes (ex: ../../etc/passwd)."""
    path = os.path.normpath(os.path.join(NOTES_DIR, filename))
    if not path.startswith(NOTES_DIR):
        raise ValueError("Chemin de fichier non autorisé.")
    return path


def list_notes() -> str:
    files = os.listdir(NOTES_DIR)
    if not files:
        return "Aucune note pour le moment."
    return "\n".join(files)


def read_note(filename: str) -> str:
    path = _safe_path(filename)
    if not os.path.exists(path):
        return f"Erreur : le fichier '{filename}' n'existe pas."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_note(filename: str, content: str) -> str:
    path = _safe_path(filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Note '{filename}' enregistrée ({len(content)} caractères)."


def execute_tool(name: str, tool_input: dict):
    """Dispatcher : appelle la bonne fonction Python selon le nom de l'outil demandé."""
    if name == "list_notes":
        return list_notes()
    elif name == "read_note":
        return read_note(**tool_input)
    elif name == "write_note":
        return write_note(**tool_input)
    else:
        return f"Erreur : outil inconnu '{name}'"
