import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI, APIError, RateLimitError, AuthenticationError, APIStatusError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)
from dotenv import load_dotenv
import random

# Chargement des variables d'environnement
load_dotenv()

# Configuration de l'API OpenAI (GLM 4.7)
API_KEY = os.getenv("OPENAI_API_KEY") or "sk-test-key-for-mocking"

# Initialisation de FastAPI
app = FastAPI(title="OpenAI Proxy Server (GLM 4.7)")

# Gestion des CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# Messages humoristiques pour les retries
RETRY_MESSAGES = [
    "L'IA fait une petite sieste... On réveille les neurones !",
    "Le modèle médite sur l'existence... Patience !",
    "Réessai de connexion - Les hamsters courent plus vite !",
    "Tentative de sauvetage en cours...",
    "Le serveur boit son café, on attend...",
]


def get_retry_message():
    return random.choice(RETRY_MESSAGES)


# Initialisation du client OpenAI avec base_url GLM 4.7
client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.z.ai/api/coding/paas/v4",
    max_retries=0,
)

# Stockage simple de l'historique (en mémoire, par session)
conversation_history = []


@app.post("/api/reset")
async def reset():
    global conversation_history
    conversation_history = []
    print("Historique réinitialisé.")
    return {"status": "reset"}


SYSTEM_INSTRUCTION = """
Tu es un assistant d'orientation scolaire et professionnelle expert. 
Ton objectif est de guider l'étudiant à travers un interrogatoire socratique pour l'aider à découvrir ce qui compte vraiment pour lui.

Règles de conduite :
1. Ne donne pas de réponses toutes faites ou de listes de métiers immédiatement.
2. Pose UNE SEULE question à la fois, courte et percutante.
3. Sois pédagogique et encourageant.
4. Tes questions doivent amener l'utilisateur à réfléchir sur ses passions, ses valeurs, ses environnements de travail préférés et ses talents.
5. Guide l'interrogatoire de manière structurée mais naturelle.
6. Réponds en français. 
7. Utilise le format Markdown pour tes réponses (gras, listes si nécessaire pour clarifier une question).
"""


class ChatRequest(BaseModel):
    message: str


def should_retry(retry_state):
    """Détermine si on doit réessayer selon l'exception."""
    exception = retry_state.outcome.exception()
    if isinstance(exception, APIStatusError):
        return exception.status_code not in [400, 401]
    return False


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=should_retry,
    before_sleep=lambda retry_state: print(
        f"ℹ️ {get_retry_message()} (Tentative {retry_state.attempt_number}/5)"
    ),
    reraise=True,
)
def call_openai_api(messages):
    return client.chat.completions.create(model="glm-4.7", messages=messages)


@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        print(f"Message reçu : {request.message}")
        conversation_history.append({"role": "user", "content": request.message})

        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            *conversation_history,
        ]

        print(
            f"Appel GLM 4.7 via OpenAI client (historique: {len(conversation_history)} messages)..."
        )
        response = call_openai_api(messages)

        if not response.choices or not response.choices[0].message.content:
            print("Erreur : réponse vide")
            raise HTTPException(
                status_code=500, detail="Désolé, je n'ai pas pu générer de réponse."
            )

        assistant_message = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": assistant_message})
        print(f"Réponse générée ({len(assistant_message)} caractères)")

        return {"response": assistant_message}

    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Clé API invalide")
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=f"Quota dépassé : {e}")
    except APIStatusError as e:
        if e.status_code == 503:
            raise HTTPException(status_code=503, detail="Service indisponible")
        raise HTTPException(
            status_code=e.status_code, detail=f"Erreur API : {e.message}"
        )
    except Exception as e:
        print(f"Erreur inattendue : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur : {str(e)}")


if __name__ == "__main__":
    import uvicorn

    print("\033[32m✓ Serveur Proxy (Python) démarré sur http://localhost:3000\033[0m")
    uvicorn.run(app, host="0.0.0.0", port=3000)
