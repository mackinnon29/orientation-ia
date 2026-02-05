import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import errors
from dotenv import load_dotenv
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# Chargement des variables d'environnement
load_dotenv()

# Configuration de l'API Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("ERREUR : La variable GEMINI_API_KEY n'est pas définie dans le fichier .env")
    exit(1)

# Initialisation de FastAPI
app = FastAPI(title="Gemini Proxy Server")

# Gestion des CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

# Initialisation du client Gemini
client = genai.Client(api_key=API_KEY)

# Stockage simple de l'historique (en mémoire, par session)
# Note: Dans une vraie appli, on utiliserait une base de données ou un cache
conversation_history = []

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

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        # Ajout du message utilisateur à l'historique
        conversation_history.append({"role": "user", "parts": [{"text": request.message}]})
        
        # Appel au SDK Gemini (v3) avec gestion des retries
        # On utilise gemini-3-flash-preview avec instruction système
        # On retente si l'erreur mentionne "503" ou "overloaded"
        
        def should_retry(exception):
            error_str = str(exception)
            return "503" in error_str or "overloaded" in error_str.lower() or "UNAVAILABLE" in error_str

        @retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception(should_retry),
            before_sleep=lambda retry_state: print(f"Tentative de retry {retry_state.attempt_number} après erreur : {retry_state.outcome.exception()}")
        )
        def generate_with_retry():
            return client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=conversation_history,
                config=genai.types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION
                )
            )

        response = generate_with_retry()
        
        if not response.text:
            raise HTTPException(status_code=500, detail="Désolé, je n'ai pas pu générer de réponse.")
        
        # Ajout de la réponse de l'IA à l'historique
        conversation_history.append({"role": "model", "parts": [{"text": response.text}]})
            
        return {"response": response.text}

    except Exception as e:
        print(f"Erreur lors de l'appel à Gemini : {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("\033[32m✓ Serveur Proxy (Python) démarré sur http://localhost:3000\033[0m")
    uvicorn.run(app, host="0.0.0.0", port=3000)
