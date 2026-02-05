import pytest
import os
import httpx
from httpx import ASGITransport, AsyncClient
from server import app, conversation_history, client
from unittest.mock import MagicMock, patch
from openai import APIStatusError, RateLimitError, AuthenticationError


@pytest.fixture(autouse=True)
def reset_conversation_history():
    """Réinitialise l'historique avant chaque test."""
    conversation_history.clear()


@pytest.mark.asyncio
async def test_chat_success():
    """Vérifie le succès d'un appel chat avec un mock de GLM 4.7."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Bonjour ! Comment puis-je vous aider ?"

    with patch.object(client.chat.completions, "create", return_value=mock_response):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/chat", json={"message": "Salut !"})

        assert response.status_code == 200
        assert response.json() == {"response": "Bonjour ! Comment puis-je vous aider ?"}
        assert len(conversation_history) == 2
        assert conversation_history[0]["role"] == "user"
        assert conversation_history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_chat_overloaded_503():
    """Vérifie que le serveur renvoie 503 après retries tenacity."""
    mock_http_response = httpx.Response(
        503, request=httpx.Request("POST", "http://test")
    )

    with patch.object(
        client.chat.completions,
        "create",
        side_effect=APIStatusError(
            message="Service overloaded",
            response=mock_http_response,
            body={"error": {"message": "Service overloaded", "type": "server_error"}},
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/chat", json={"message": "Tester 503"})

        assert response.status_code == 503
        assert "indisponible" in response.json()["detail"].lower()
        # 5 tentatives (1 initiale + 4 retries)
        assert client.chat.completions.create.call_count == 5


@pytest.mark.asyncio
async def test_chat_quota_exceeded_429():
    """Vérifie que le serveur renvoie 429 après retries tenacity."""
    mock_http_response = httpx.Response(
        429, request=httpx.Request("POST", "http://test")
    )

    with patch.object(
        client.chat.completions,
        "create",
        side_effect=RateLimitError(
            message="Rate limit exceeded",
            response=mock_http_response,
            body={
                "error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}
            },
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/chat", json={"message": "Tester 429"})

        assert response.status_code == 429
        assert (
            "quota" in response.json()["detail"].lower()
            or "rate" in response.json()["detail"].lower()
        )
        # 5 tentatives (1 initiale + 4 retries)
        assert client.chat.completions.create.call_count == 5


@pytest.mark.asyncio
async def test_chat_authentication_error_401():
    """Vérifie la gestion d'une erreur d'authentification."""
    mock_http_response = httpx.Response(
        401, request=httpx.Request("POST", "http://test")
    )

    with patch.object(
        client.chat.completions,
        "create",
        side_effect=AuthenticationError(
            message="Invalid API key",
            response=mock_http_response,
            body={
                "error": {"message": "Invalid API key", "type": "invalid_request_error"}
            },
        ),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/chat", json={"message": "Tester 401"})

        assert response.status_code == 401
        assert (
            "clé" in response.json()["detail"].lower()
            or "api" in response.json()["detail"].lower()
        )
        # Pas de retry pour AuthenticationError
        assert client.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_chat_empty_response_error():
    """Vérifie la gestion d'une réponse vide de GLM 4.7."""
    mock_response = MagicMock()
    mock_response.choices = []

    with patch.object(client.chat.completions, "create", return_value=mock_response):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/chat", json={"message": "Msg vide"})

        assert response.status_code == 500
        assert "Désolé" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_fatal_error():
    """Vérifie la gestion d'une erreur fatale de l'API."""
    with patch.object(
        client.chat.completions,
        "create",
        side_effect=Exception("Erreur critique inattendue"),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/chat", json={"message": "Crash test"})

        assert response.status_code == 500
        assert "Erreur critique inattendue" in response.json()["detail"]


@pytest.mark.asyncio
async def test_conversation_history_persistence():
    """Vérifie que l'historique s'accumule correctement."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Réponse"

    with patch.object(client.chat.completions, "create", return_value=mock_response):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            await ac.post("/api/chat", json={"message": "Msg 1"})
            await ac.post("/api/chat", json={"message": "Msg 2"})

        # 2 messages utilisateur + 2 messages assistant
        assert len(conversation_history) == 4
        assert conversation_history[0]["content"] == "Msg 1"
        assert conversation_history[2]["content"] == "Msg 2"
        assert conversation_history[1]["role"] == "assistant"
        assert conversation_history[3]["role"] == "assistant"
