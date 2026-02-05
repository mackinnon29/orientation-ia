# AGENTS.md - Orientation IA

## Build/Lint/Test Commands

### Python Backend

```bash
# Run all tests
pytest

# Run a single test
pytest tests/test_server.py::test_chat_success -v

# Run tests with verbose output
pytest -v

# Run server
python server.py
# or
uv run server.py
```

## Workflow de Développement

1. **Démarrer le backend** : `python server.py` (écoute sur port 3000)
2. **Ouvrir le frontend** : Serveur local (http-server, Live Server, etc.) sur index.html
3. **Tests** : Toujours lancer `pytest` avant de commiter
4. **Git** : Commits en français, messages descriptifs

## Project Structure

- `server.py` - FastAPI backend server with Gemini integration
- `tests/test_server.py` - Pytest async tests with mocking
- `js/app.js` - Frontend application logic
- `js/ai-service.js` - AI service (mock + Gemini proxy)
- `css/style.css` - Glassmorphism UI styles
- `index.html` - Main HTML page

## Code Style Guidelines

### Python (Backend)

**Imports:**
- Standard library first (os, unittest.mock)
- Third-party packages next (fastapi, pytest, httpx)
- Local modules last
- Group imports with blank lines between groups

**Formatting:**
- Use descriptive French variable names where appropriate
- Follow PEP 8 conventions
- Use type hints for function parameters and return types
- Docstrings in French for user-facing features

**Error Handling:**
- Use FastAPI's `HTTPException` for HTTP errors
- Log errors with `print()` for debugging
- Implement retry logic with `tenacity` for external API calls
- Return meaningful error messages in French to users

**Testing:**
- Use `pytest-asyncio` for async tests
- Mock external API calls (Gemini client)
- Use fixtures for setup/teardown (`@pytest.fixture(autouse=True)`)
- Clear test names describing the scenario
- Assert on both status codes and response content
- Patch `tenacity.nap.time.sleep` in retry tests to avoid delays

### JavaScript (Frontend)

**Style:**
- Use ES6+ features (const/let, arrow functions, async/await)
- JSDoc comments for function documentation
- French comments and user-facing strings
- Semicolons optional but be consistent

**Naming:**
- `camelCase` for variables and functions
- `PascalCase` for service objects/classes
- Descriptive names (e.g., `addLoadingIndicator` not `loading`)

**Error Handling:**
- Wrap async calls in try/catch
- Provide user-friendly fallback messages
- Log errors to console for debugging
- Service fallback: GeminiService → MockAiService on error

**Service Pattern:**
- `MockAiService` : Simulation locale sans backend
- `GeminiService` : 
    - Appel au proxy Python (localhost:3000) qui appelle Gemini 3.0 flash (gemini-3-flash-preview)
    - LIRE IMPERATIVEMENT https://ai.google.dev/gemini-api/docs/gemini-3.md.txt
- `AiService` : Sélecteur (changez pour MockAiService en développement)

### CSS

**Organization:**
- CSS variables in `:root` for theming
- BEM-like naming for components
- Mobile-first responsive design
- French comments for sections

**Naming:**
- `kebab-case` for class names
- Semantic naming (e.g., `chat-messages` not `box1`)

**Design System:**
- Glassmorphism: `.glass` class with backdrop-filter
- Color palette: emerald/cyber-blue gradients
- Animations: fadeIn, messageSlide, bounce

## Architecture API

```
Frontend (js) → Proxy Python (localhost:3000) → Gemini API
              ↓
         Retry Logic (tenacity)
              ↓
         Memory Conversation History
```

- **Endpoint POST** `/api/chat` avec JSON `{message: str}`
- **Retry Strategy** : 5 tentatives, backoff exponentiel (1-10s)
- **Conditions de retry** : Erreurs 503, "overloaded", "UNAVAILABLE"
- **CORS** : Autorisé pour tous origins (restreindre en prod)

## Environment Setup

```bash
# Copy environment file
cp .env.example .env

# Add your Gemini API key to .env
# GEMINI_API_KEY=your_key_here
```

## Dependencies

Managed with `uv` (modern Python package manager):
- FastAPI + Uvicorn for backend
- Google GenAI SDK for Gemini API
- Tenacity for retry logic
- Pytest + pytest-asyncio for testing
- HTTPX for async HTTP client in tests

## Key Implementation Notes

- Backend runs on port 3000
- CORS enabled for all origins (restrict in production)
- Conversation history stored in memory (use Redis/DB in production)
- Frontend falls back to mock service if backend unavailable
- System instructions in French for Gemini prompts
- Frontend uses CDN for marked.js (Markdown parsing)

## Language Conventions

- **Code** : Anglais (noms de variables, fonctions, classes)
- **Comments** : Français (explications, docstrings)
- **User-facing strings** : Français (messages d'erreur, UI text)
- **Commit messages** : Français (descriptifs et courts)
