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


# Tests pour le comportement caustique
from server import is_weak_response, score_user_response, WEAK_WORDS


def test_is_weak_response_with_forbidden_words():
    """Vérifie que les mots interdits sont détectés."""
    for word in ["désolé", "comprends", "pas de souci", "excellent"]:
        assert is_weak_response(f"Je suis {word} de t'aider") is True


def test_is_weak_response_with_short_response():
    """Vérifie que les réponses courtes sans question sont détectées."""
    assert is_weak_response("ok") is True
    assert is_weak_response("d'accord") is True
    assert is_weak_response("je vois") is True
    assert is_weak_response("c'est bien") is True


def test_is_weak_response_with_question():
    """Vérifie qu'une question courte n'est pas faible."""
    assert is_weak_response("Tu aimes ça ?") is False


def test_is_weak_response_with_strong_response():
    """Vérifie qu'une réponse longue et significative n'est pas faible."""
    assert (
        is_weak_response(
            "J'adore travailler avec les ordinateurs et créer des applications"
        )
        is False
    )


def test_score_user_response_length():
    """Vérifie le scoring basé sur la longueur."""
    # Court (< 20 caractères) = 0 point pour la longueur
    # Mais peut avoir des points pour l'absence d'évitement
    short_score = score_user_response("ok")
    assert (
        short_score <= 5
    )  # Court mais sans évitement = max 4 points (évitement) + 0 (longueur) + 0 (mots)
    # Moyen (20-50 caractères) = 1 point
    assert score_user_response("J'aime bien travailler avec les ordis") >= 1
    # Long (50-100 caractères) = 2 points
    assert (
        score_user_response("J'aime bien travailler avec les ordinateurs et programmer")
        >= 2
    )
    # Très long (>= 100 caractères) = 3 points
    assert (
        score_user_response(
            "Je suis passionné par l'informatique depuis mon enfance et j'adore créer des applications web modernes"
        )
        >= 3
    )


def test_score_user_response_significant_words():
    """Vérifie le scoring basé sur les mots significatifs."""
    # Aucun mot significatif
    assert score_user_response("je sais pas") <= 2
    # 1 mot significatif
    assert score_user_response("j'aime le métier") >= 1
    # 2 mots significatifs
    assert score_user_response("j'aime mon métier et ma passion") >= 2
    # 3+ mots significatifs
    assert (
        score_user_response("mon métier ma passion mes compétences en informatique")
        >= 3
    )


def test_score_user_response_avoidance():
    """Vérifie le scoring basé sur l'absence d'évitement."""
    # Beaucoup d'évitement = faible score
    assert score_user_response("je sais pas, euh, bah, rien") <= 3
    # Peu d'évitement = score moyen
    assert score_user_response("je sais pas mais j'aime les ordis") >= 3
    # Pas d'évitement = bon score
    assert score_user_response("J'adore programmer et créer des applications web") >= 6


@pytest.mark.asyncio
async def test_caustic_behavior():
    """Vérifie que le mode caustic utilise les bons paramètres."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Réponse caustique"

    with patch.object(
        client.chat.completions, "create", return_value=mock_response
    ) as mock_create:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/chat", json={"message": "je sais pas", "behavior": "caustic"}
            )

        assert response.status_code == 200
        # Vérifie que les paramètres caustiques sont utilisés
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["temperature"] == 0.9
        assert call_kwargs["frequency_penalty"] == 0.5
        assert call_kwargs["presence_penalty"] == 0.3


@pytest.mark.asyncio
async def test_caustic_few_shot_examples():
    """Vérifie que les exemples few-shot sont présents dans le prompt caustique."""
    from server import CAUSTIC_BEHAVIOR

    # Vérifie la présence des exemples few-shot
    assert 'User: "je sais pas"' in CAUSTIC_BEHAVIOR
    assert 'User: "rien"' in CAUSTIC_BEHAVIOR
    assert 'User: "bah quoi"' in CAUSTIC_BEHAVIOR
    assert 'User: "je sais pas quoi faire"' in CAUSTIC_BEHAVIOR
    assert 'User: "aucune idée"' in CAUSTIC_BEHAVIOR

    # Vérifie les réponses attendues
    assert "Je ne vais pas choisir à ta place" in CAUSTIC_BEHAVIOR
    assert "Décide-toi, j'ai pas le temps" in CAUSTIC_BEHAVIOR
    assert "Grouille-toi de choisir" in CAUSTIC_BEHAVIOR
    assert "Pathétique" in CAUSTIC_BEHAVIOR
    assert "Dépêche-toi ma patience a des limites" in CAUSTIC_BEHAVIOR

    # Vérifie l'interdiction des insultes
    assert "vulgarité" in CAUSTIC_BEHAVIOR.lower()
    assert "insultes" in CAUSTIC_BEHAVIOR.lower()
    # Vérifie que "ignorant" n'apparaît pas dans les exemples de réponses (mais peut être dans les règles)
    examples_section = CAUSTIC_BEHAVIOR.split("EXEMPLES DE RÉPONSES ATTENDUES :")[1]
    assert "ignorant" not in examples_section.lower()
