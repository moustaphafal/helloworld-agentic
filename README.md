# Agent de notes — projet minimal

Un agent en ligne de commande qui peut lister, lire et écrire des fichiers de
notes texte dans un dossier local, via l'API Claude et le tool use.

## Structure

```
agent-project/
├── agent.py          # boucle principale : conversation + exécution des outils
├── tools.py          # schémas des outils + leur implémentation Python
├── requirements.txt
├── .env.example
└── notes/            # créé automatiquement au premier lancement
```

## Installation

1. Crée un environnement virtuel (recommandé) :
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
   Dans PowerShell, active-le avec `\.venv\Scripts\Activate.ps1`. Si PowerShell
   bloque l'exécution du script, autorise-la uniquement dans cette fenêtre :
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

2. Installe les dépendances :
   ```bash
   pip install -r requirements.txt
   ```

3. Choisis le fournisseur du modèle. Claude est utilisé par défaut. Dans PowerShell :
   ```powershell
   $env:LLM_PROVIDER = "anthropic"
   $env:ANTHROPIC_API_KEY = "ta-cle-api"
   ```
   Pour utiliser un modèle local avec LM Studio : démarre le serveur local dans
   LM Studio (par défaut `http://localhost:1234/v1`), charge un modèle qui prend
   en charge les appels d'outils, puis configure son identifiant :
   ```powershell
   $env:LLM_PROVIDER = "lmstudio"
   $env:LM_STUDIO_MODEL = "identifiant-du-modele-charge"
   ```
   `LM_STUDIO_BASE_URL` peut être défini si le serveur utilise une autre adresse.
   Aucun compte ni clé API Anthropic n'est requis en mode LM Studio. Ces variables
   d'environnement doivent être définies à nouveau dans chaque nouveau terminal.

## Lancer l'agent

```bash
python agent.py
```

Exemples de choses à lui dire :
- "Liste mes notes"
- "Crée une note 'idees.txt' avec trois idées de side-projects"
- "Qu'est-ce qu'il y a dans idees.txt ?"

## Comment ça marche (résumé)

1. `tools.py` décrit chaque outil avec un schéma JSON (nom, description,
   paramètres attendus). C'est ce schéma que le modèle lit pour savoir
   quels outils existent et comment les appeler.
2. `agent.py` envoie la conversation + ces schémas à l'API.
3. Si le modèle décide d'utiliser un outil, la réponse contient un bloc
   `tool_use` avec le nom de l'outil et les arguments choisis par le modèle.
4. Le script exécute la vraie fonction Python correspondante (`execute_tool`),
   et renvoie le résultat au modèle sous forme de `tool_result`.
5. Le modèle continue avec ce résultat en main — il peut enchaîner un autre
   outil, ou répondre en texte normal. La boucle s'arrête quand il n'y a
   plus de demande d'outil.

## Pour aller plus loin

- Ajoute un nouvel outil dans `tools.py` (ex: appeler une API météo, lire un
  CSV) — ajoute juste son schéma dans `TOOLS` et son cas dans `execute_tool`.
- Ajoute une étape de confirmation humaine avant `write_note` si tu veux
  simuler une action "sensible" (bonne pratique pour tout outil qui modifie
  des données réelles).
- Sauvegarde `conversation` dans un fichier JSON entre les sessions si tu veux
  que l'agent garde la mémoire d'une fois sur l'autre.
