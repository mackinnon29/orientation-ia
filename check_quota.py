import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

try:
    print("Tentative d'appel à Gemini 3 Flash Preview...")
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents="Bonjour, es-tu actif ?",
    )
    print(f"Réponse reçue : {response.text}")
except Exception as e:
    print(f"Erreur lors du test direct : {e}")
