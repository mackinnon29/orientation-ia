import pytest
import os
from httpx import ASGITransport, AsyncClient
from server import app, conversation_history
from unittest.mock import MagicMock, patch

@pytest.fixture(autouse=True)
def reset_conversation_history():
    """Réinitialise l'historique avant chaque test."""
    conversation_history.clear()

@pytest.mark.asyncio
async def test_chat_success():
    """Vérifie le succès d'un appel chat avec un mock de Gemini."""
    with patch("server.client.models.generate_content") as mock_gen:
        # Mock de la réponse Gemini
        mock_response = MagicMock()
        mock_response.text = "Bonjour ! Comment puis-je vous aider ?"
        mock_gen.return_value = mock_response

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/chat", json={"message": "Salut !"})

        assert response.status_code == 200
        assert response.json() == {"response": "Bonjour ! Comment puis-je vous aider ?"}
        assert len(conversation_history) == 2
        assert conversation_history[0]["role"] == "user"
        assert conversation_history[1]["role"] == "model"

@pytest.mark.asyncio
async def test_chat_gemini_overloaded_retry():
    """Vérifie que le retry fonctionne en cas de 503."""
    with patch("server.client.models.generate_content") as mock_gen:
        # Configuration : 2 échecs 503 puis un succès
        mock_success = MagicMock()
        mock_success.text = "Réponse après retry"
        
        mock_gen.side_effect = [
            Exception("503 UNAVAILABLE: Model is overloaded"),
            Exception("503 UNAVAILABLE: Still overloaded"),
            mock_success
        ]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # On utilise un timeout plus long car tenacity va attendre entre les retries
            # Mais ici on a configuré server.py pour attendre, donc le test peut être lent
            # Pour accélérer le test, on pourrait patcher tenacity.wait_exponential
            with patch("tenacity.nap.time.sleep", return_value=None):
                response = await ac.post("/api/chat", json={"message": "Tester le retry"})

        assert response.status_code == 200
        assert response.json()["response"] == "Réponse après retry"
        assert mock_gen.call_count == 3

@pytest.mark.asyncio
async def test_chat_empty_response_error():
    """Vérifie la gestion d'une réponse vide de Gemini."""
    with patch("server.client.models.generate_content") as mock_gen:
        mock_response = MagicMock()
        mock_response.text = None
        mock_gen.return_value = mock_response

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/chat", json={"message": "Msg vide"})

        assert response.status_code == 500
        assert "Désolé" in response.json()["detail"]

@pytest.mark.asyncio
async def test_chat_fatal_error():
    """Vérifie la gestion d'une erreur fatale de l'API."""
    with patch("server.client.models.generate_content") as mock_gen:
        mock_gen.side_effect = Exception("Erreur critique inattendue")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/chat", json={"message": "Crash test"})

        assert response.status_code == 500
        assert "Erreur critique inattendue" in response.json()["detail"]

@pytest.mark.asyncio
async def test_conversation_history_persistence():
    """Vérifie que l'historique s'accumule correctement."""
    with patch("server.client.models.generate_content") as mock_gen:
        mock_response = MagicMock()
        mock_response.text = "Réponse"
        mock_gen.return_value = mock_response

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            await ac.post("/api/chat", json={"message": "Msg 1"})
            await ac.post("/api/chat", json={"message": "Msg 2"})

        # 2 messages utilisateur + 2 messages modèle
        assert len(conversation_history) == 4
        assert conversation_history[0]["parts"][0]["text"] == "Msg 1"
        assert conversation_history[2]["parts"][0]["text"] == "Msg 2"
