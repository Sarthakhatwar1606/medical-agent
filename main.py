"""
FastAPI server — production-ready REST API for the medical agent.

Endpoints:
  POST /chat           — send a message, get a response
  DELETE /chat/{sid}   — clear a session
  GET  /health         — liveness probe (for Azure App Service / Container Apps)
"""

import logging
import uuid
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from agent import run_agent
from config import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# Validate required env vars at startup — fail fast rather than at first request
config.validate()

app = FastAPI(
    title="Medical AI Agent",
    description="AI-powered medical information assistant powered by Claude on Azure AI Foundry",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Restrict to your frontend domain in production
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory session store
# In production: replace with Azure Cosmos DB or Azure Cache for Redis
# ---------------------------------------------------------------------------
_sessions: dict[str, list[dict]] = {}
MAX_HISTORY_MESSAGES = 20   # caps context window usage

DISCLAIMER = (
    "\n\n⚠️ **Medical Disclaimer:** This information is for educational purposes only "
    "and does not constitute medical advice. Always consult a qualified healthcare "
    "professional before starting, changing, or stopping any treatment or medication."
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = Field(
        default=None,
        description="Omit to start a new session; include to continue an existing one.",
    )


class ChatResponse(BaseModel):
    session_id: str
    response: str
    disclaimer: str


class HealthResponse(BaseModel):
    status: str
    model: str
    search_index: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    """Send a message to the medical agent and receive a response."""
    session_id = body.session_id or str(uuid.uuid4())
    history = _sessions.get(session_id, [])

    try:
        response_text, updated_history = run_agent(body.message, history)
    except RuntimeError as exc:
        logger.error("Agent error for session %s: %s", session_id, exc)
        raise HTTPException(status_code=500, detail="Agent processing failed. Please try again.")
    except Exception as exc:
        logger.exception("Unexpected error for session %s", session_id)
        raise HTTPException(status_code=500, detail=str(exc))

    # Persist updated history, capping at MAX_HISTORY_MESSAGES
    _sessions[session_id] = updated_history[-MAX_HISTORY_MESSAGES:]

    return ChatResponse(
        session_id=session_id,
        response=response_text,
        disclaimer=DISCLAIMER,
    )


@app.delete("/chat/{session_id}")
def clear_session(session_id: str) -> dict:
    """Clear conversation history for the given session."""
    _sessions.pop(session_id, None)
    return {"message": f"Session '{session_id}' cleared."}


@app.get("/")
def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness probe for Azure App Service / Container Apps health checks."""
    return HealthResponse(
        status="healthy",
        model=config.MODEL,
        search_index=config.SEARCH_INDEX,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,       # Set True only during local development
        log_level="info",
    )
