"""
Agent IA minimal avec Claude ou un modèle local via LM Studio.
============================================================

Ce script montre la boucle de base d'un agent :
1. On envoie la conversation + la liste des outils disponibles au modèle
2. Le modèle répond soit avec du texte, soit avec une demande d'utiliser un outil
3. Si c'est un outil, on l'exécute nous-mêmes et on renvoie le résultat au modèle
4. On boucle jusqu'à ce que le modèle donne une réponse finale (pas de tool_use)

Prérequis :
- pip install -r requirements.txt
- ANTHROPIC_API_KEY si LLM_PROVIDER=anthropic
- LM Studio lancé si LLM_PROVIDER=lmstudio
"""

import json
import os
from anthropic import Anthropic
from openai import OpenAI
from tools import TOOLS, execute_tool

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "local-model")
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
MAX_ITERATIONS = 8  # sécurité : on évite qu'une boucle d'outils tourne à l'infini

_client = None

SYSTEM_PROMPT = """Tu es un assistant qui aide à gérer des notes texte dans un dossier local.
Tu as accès à des outils pour lister, lire et écrire des notes.
Utilise-les quand c'est pertinent plutôt que d'inventer des réponses.
Sois concis dans tes réponses."""


def _get_client():
    global _client
    if _client is None:
        if LLM_PROVIDER == "anthropic":
            _client = Anthropic()
        elif LLM_PROVIDER == "lmstudio":
            _client = OpenAI(
                base_url=LM_STUDIO_BASE_URL,
                api_key=os.getenv("LM_STUDIO_API_KEY", "lm-studio"),
            )
        else:
            raise ValueError(
                f"Fournisseur inconnu '{LLM_PROVIDER}'. "
                "Valeurs acceptées : anthropic, lmstudio."
            )
    return _client


def _openai_tools() -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        for tool in TOOLS
    ]


def _openai_messages(conversation: list) -> list:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for message in conversation:
        if message["role"] == "assistant" and message.get("tool_calls"):
            messages.append({
                "role": "assistant",
                "content": message["content"] or None,
                "tool_calls": [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call["input"]),
                        },
                    }
                    for call in message["tool_calls"]
                ],
            })
        else:
            messages.append(message.copy())
    return messages


def _anthropic_messages(conversation: list) -> list:
    messages = []
    index = 0
    while index < len(conversation):
        message = conversation[index]
        if message["role"] == "tool":
            results = []
            while index < len(conversation) and conversation[index]["role"] == "tool":
                tool_result = conversation[index]
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_result["tool_call_id"],
                    "content": tool_result["content"],
                })
                index += 1
            messages.append({"role": "user", "content": results})
            continue

        if message["role"] == "assistant" and message.get("tool_calls"):
            content = []
            if message["content"]:
                content.append({"type": "text", "text": message["content"]})
            content.extend(
                {
                    "type": "tool_use",
                    "id": call["id"],
                    "name": call["name"],
                    "input": call["input"],
                }
                for call in message["tool_calls"]
            )
            messages.append({"role": "assistant", "content": content})
        else:
            messages.append({"role": message["role"], "content": message["content"]})
        index += 1
    return messages


def run_agent(user_message: str, conversation: list) -> list:
    """
    Envoie un message utilisateur à l'agent, exécute les outils demandés,
    et renvoie la conversation mise à jour (avec la réponse finale du modèle dedans).
    """
    conversation.append({"role": "user", "content": user_message})

    for _ in range(MAX_ITERATIONS):
        if LLM_PROVIDER == "anthropic":
            response = _get_client().messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=_anthropic_messages(conversation),
            )
            assistant_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            tool_calls = [
                {
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                }
                for block in response.content
                if block.type == "tool_use"
            ]
        elif LLM_PROVIDER == "lmstudio":
            response = _get_client().chat.completions.create(
                model=LM_STUDIO_MODEL,
                messages=_openai_messages(conversation),
                tools=_openai_tools(),
                tool_choice="auto",
                max_tokens=1024,
            )
            assistant_message = response.choices[0].message
            assistant_text = assistant_message.content or ""
            tool_calls = [
                {
                    "id": call.id,
                    "name": call.function.name,
                    "input": json.loads(call.function.arguments or "{}"),
                }
                for call in (assistant_message.tool_calls or [])
            ]
        else:
            _get_client()

        conversation.append({
            "role": "assistant",
            "content": assistant_text,
            "tool_calls": tool_calls,
        })

        if not tool_calls:
            break

        for call in tool_calls:
            print(f"  -> L'agent utilise l'outil : {call['name']}({call['input']})")
            result = execute_tool(call["name"], call["input"])
            conversation.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": str(result),
            })
    else:
        print("  !! Limite d'itérations atteinte, arrêt de sécurité.")

    return conversation


def main():
    print("Agent de notes - tape 'quit' pour sortir\n")
    conversation = []

    while True:
        user_input = input("Toi: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        if not user_input:
            continue

        conversation = run_agent(user_input, conversation)

        last_message = conversation[-1]
        if last_message["role"] == "assistant" and last_message["content"]:
            print(f"Agent: {last_message['content']}\n")


if __name__ == "__main__":
    main()
