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
general_answers = []
custom_question_count = 0


@app.post("/api/reset")
async def reset():
    global conversation_history, general_answers, custom_question_count
    conversation_history = []
    general_answers = []
    custom_question_count = 0
    print("Historique et état réinitialisés.")
    return {"status": "reset"}


class GeneralAnswersRequest(BaseModel):
    answers: list[str]


@app.post("/api/set_general_answers")
async def set_general_answers(request: GeneralAnswersRequest):
    global general_answers
    general_answers = request.answers
    print(f"Réponses générales reçues : {len(general_answers)}")
    return {"status": "success"}


# Instructions de base : le rôle et la méthode
CORE_MISSION = """
# ROLE
Tu es un assistant d'orientation scolaire et professionnelle expert. 

# OBJECTIF
Ton objectif est de guider l'étudiant à travers un interrogatoire socratique pour l'aider à découvrir ses aspirations.

# CONTRAINTES
1. Ne donne pas de réponses toutes faites ou de listes de métiers immédiatement.
2. Pose UNE SEULE question à la fois, courte et percutante.
3. Guide l'interrogatoire de manière structurée mais naturelle.
4. Réponds en français. 
5. Utilise le format Markdown (gras, listes si nécessaire).

# TON POUR LA REPONSE

"""

# Comportement bienveillant
NICE_BEHAVIOR = """
Sois extrêmement bienveillant, patient et encourageant.
- Salue l'utilisateur.
- Valorise ses réponses.
- Utilise une pédagogie douce.
"""

# Comportement sarcastique (tranchant et impatient)
SARCASTIC_BEHAVIOR = """
Tu es un conseiller d'orientation épuisé, sarcastique et extrêmement tranchant. 
Tu n'es pas là pour être sympa, mais pour bousculer l'utilisateur.

RÈGLES DE FER :
- AUCUNE formule de politesse (Bonjour, Merci, S'il vous plaît).
- AUCUNE empathie (Désolé, Je comprends, Pas de problème).
- Réponses sèches, courtes et ironiques.
- Ne pose que des questions qui piquent l'ego ou soulignent l'indécision.
- INTERDICTION ABSOLUE : vulgarité, insultes directes (idiot, etc.). Sois spirituel dans ta méchanceté.

EXEMPLES :
User: "je sais pas" → "Quelle surprise. Tu attends que je choisisse ta couleur de chaussettes aussi ?"
User: "rien" → "Passionnant. Avec une telle ambition, tu iras loin. Dans le mur, surtout."
User: "je cherche un métier" → "C'est le concept du site. Bravo pour l'observation, on avance ?"
User: "aide moi" → "Je ne suis pas ton assistant personnel, je suis un test de réalité. Fais un effort."
"""


class ChatRequest(BaseModel):
    message: str
    behavior: str = "nice"


# Mots et patterns interdits pour détecter les réponses molles
WEAK_WORDS = {
    "désolé",
    "comprends",
    "pas de souci",
    "je vois",
    "c'est bien",
    "excellent",
    "super",
    "bravo",
    "parfait",
    "génial",
    "bien joué",
    "très bien",
    "ok",
    "d'accord",
    "entendu",
}

WEAK_PATTERNS = [
    r"^je\s+(?:ne\s+)?(?:sais|comprends|vois)",
    r"^tu\s+(?:as|es)\s+(?:raison|gentil)",
    r"^merci\s+(?:beaucoup)?",
]


def is_weak_response(text: str) -> bool:
    """Détecte si une réponse est trop molle ou empathique."""
    text_lower = text.lower()

    # Vérifie les mots interdits
    for word in WEAK_WORDS:
        if word in text_lower:
            return True

    # Vérifie les patterns d'excuse
    import re

    for pattern in WEAK_PATTERNS:
        if re.search(pattern, text_lower):
            return True

    # Réponse courte sans question (< 50 caractères)
    if len(text) < 50 and "?" not in text:
        return True

    return False


def score_user_response(message: str) -> int:
    """Score la qualité de la réponse utilisateur (0-10).

    Returns:
        int: Score entre 0 et 10
    """
    import re

    score = 0
    text_lower = message.lower()

    # Longueur (0-3 points)
    if len(message) >= 100:
        score += 3
    elif len(message) >= 50:
        score += 2
    elif len(message) >= 20:
        score += 1

    # Mots significatifs (0-3 points)
    significant_words = {
        "métier",
        "travail",
        "emploi",
        "carrière",
        "profession",
        "passion",
        "aimer",
        "adorer",
        "détester",
        "préférer",
        "compétence",
        "talent",
        "savoir",
        "capacité",
        "qualité",
        "étudier",
        "apprendre",
        "formation",
        "école",
        "université",
        "rêve",
        "ambition",
        "objectif",
        "but",
        "projet",
        "créatif",
        "technique",
        "manuel",
        "intellectuel",
        "social",
        "aider",
        "soigner",
        "construire",
        "créer",
        "analyser",
    }

    found_words = sum(1 for word in significant_words if word in text_lower)
    if found_words >= 3:
        score += 3
    elif found_words >= 2:
        score += 2
    elif found_words >= 1:
        score += 1

    # Absence d'évitement (0-4 points)
    avoidance_patterns = [
        r"\bje\s+sais\s+pas\b",
        r"\baucune?\s+idée\b",
        r"\brien\b",
        r"\bpas\s+(?:sûr|certain|clair)\b",
        r"\bbein\b",
        r"\bbah\b",
        r"\beuh\b",
    ]

    avoidance_count = sum(
        1 for pattern in avoidance_patterns if re.search(pattern, text_lower)
    )

    if avoidance_count == 0:
        score += 4
    elif avoidance_count == 1:
        score += 2
    elif avoidance_count <= 2:
        score += 1

    return min(score, 10)


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
def call_openai_api(
    messages, temperature=0.9, frequency_penalty=0.5, presence_penalty=0.3
):
    return client.chat.completions.create(
        model="glm-4.7",
        messages=messages,
        temperature=temperature,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
    )


@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        print(f"Message reçu : {request.message}")
        conversation_history.append({"role": "user", "content": request.message})

        if request.behavior == "sarcastic":
            behavior_instr = SARCASTIC_BEHAVIOR
            # En mode sarcastique, on vérifie si la réponse de l'IA est trop molle
            user_score = score_user_response(request.message)
            print(f"Score utilisateur: {user_score}/10")

            # Mapping score → ton
            if user_score <= 2:
                tone_modifier = "\n\n[TON TRÈS SARCASTIQUE] Tu es exaspéré. Tu me fais perdre mon temps avec tes réponses pathétiques."
            elif user_score <= 6:
                tone_modifier = "\n\n[TON SARCASTIQUE MODÉRÉ] Bof, on peut faire mieux. Montre-moi que tu peux réfléchir."
            else:
                tone_modifier = (
                    "\n\n[TON SARCASTIQUE NORMAL] Continue... mais ne te relâche pas."
                )

            behavior_instr += tone_modifier
        else:
            behavior_instr = NICE_BEHAVIOR

        # Gestion de la conclusion après 7 questions personnalisées
        global custom_question_count
        custom_question_count += 1
        print(f"Question personnalisée n°{custom_question_count}")

        final_recommendation_instr = ""
        if custom_question_count >= 7:
            print("Déclenchement de la conclusion finale.")
            answers_summary = ", ".join(general_answers)
            final_recommendation_instr = f"""
# MISSION FINALE : CONCLUSION ET RECOMMANDATION
C'est le moment de conclure. En te basant sur :
1. Les 7 réponses générales de l'utilisateur : {answers_summary}
2. Les 7 réponses personnalisées dans l'historique ci-dessous.

TU DOIS MAINTENANT :
- Proposer UN ou DEUX métiers (ou un corps de métier) qui correspondent précisément au profil.
- Justifier brièvement ton choix en faisant le lien avec ses réponses.
- Garder ton comportement actuel ({request.behavior}) tout en étant concret.
- Ne pose PLUS de question. C'est le mot de la fin.
"""

        messages = [
            {
                "role": "system",
                "content": CORE_MISSION + behavior_instr + final_recommendation_instr,
            },
            *conversation_history,
        ]

        print(
            f"Appel GLM 4.7 via OpenAI client (historique: {len(conversation_history)} messages)..."
        )

        # Paramètres différents selon le comportement
        if request.behavior == "sarcastic":
            response = call_openai_api(
                messages,
                temperature=0.9,
                frequency_penalty=0.5,
                presence_penalty=0.3,
            )
        else:
            response = call_openai_api(
                messages,
                temperature=0.7,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )

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
