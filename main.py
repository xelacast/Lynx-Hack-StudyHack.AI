"""
Anki Flashcard Generator API
-----------------------------
FastAPI service that creates Anki decks and adds Basic (Front/Back) cards
via AnkiConnect (https://git.sr.ht/~foosoft/anki-connect).

Prerequisites:
  1. Anki must be running with the AnkiConnect add-on installed (code 2055492159).
  2. AnkiConnect listens on http://127.0.0.1:8765 by default.

Usage:
  uvicorn main:app --reload --port 8000
"""

import json
import os
import urllib.request
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ANKI_CONNECT_URL = os.environ.get("ANKI_CONNECT_URL", "http://127.0.0.1:8765")
ANKI_CONNECT_VERSION = 6

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class Cards(BaseModel):
    questions: list[str]
    answers: list[str]
    tags: list[str] = []

class DeckRequest(BaseModel):
    topic: str
    cards: Cards

    @field_validator("topic")
    @classmethod
    def topic_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("topic must not be empty")
        return v.strip()

    @field_validator("cards")
    @classmethod
    def questions_answers_same_length(cls, v: Cards) -> Cards:
        if len(v.questions) != len(v.answers):
            raise ValueError(
                f"questions ({len(v.questions)}) and answers ({len(v.answers)}) "
                "must have the same length"
            )
        if len(v.questions) == 0:
            raise ValueError("at least one question/answer pair is required")
        return v

class DeckResponse(BaseModel):
    status: str
    deck_id: int
    cards_created: int
    note_ids: list[Optional[int]]
    errors: list[str]

# ---------------------------------------------------------------------------
# AnkiConnect helper
# ---------------------------------------------------------------------------

def anki_request(action: str, **params) -> dict:
    """Send a request to AnkiConnect and return the raw response dict."""
    payload = json.dumps({
        "action": action,
        "version": ANKI_CONNECT_VERSION,
        "params": params,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(ANKI_CONNECT_URL, payload)
        response = json.load(urllib.request.urlopen(req))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Could not reach AnkiConnect at {ANKI_CONNECT_URL}. "
                "Make sure Anki is running with the AnkiConnect add-on installed. "
                f"Error: {exc}"
            ),
        )

    if len(response) != 2:
        raise HTTPException(status_code=502, detail="Unexpected AnkiConnect response format")
    if "error" not in response or "result" not in response:
        raise HTTPException(status_code=502, detail="AnkiConnect response missing required fields")

    return response


def anki_invoke(action: str, **params):
    """Send a request and return only the result, raising on errors."""
    response = anki_request(action, **params)
    if response["error"] is not None:
        raise HTTPException(status_code=400, detail=f"AnkiConnect error: {response['error']}")
    return response["result"]

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Anki Flashcard Generator",
    description="Create Anki decks and flashcards via AnkiConnect",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    """Verify that AnkiConnect is reachable."""
    try:
        version = anki_invoke("version")
        return {"status": "ok", "anki_connect_version": version}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/create-deck", response_model=DeckResponse)
async def create_deck(request: DeckRequest):
    """
    Create (or reuse) an Anki deck and populate it with Basic flashcards.

    Request body example:
    ```json
    {
      "topic": "Python Basics",
      "cards": {
        "questions": ["What is a list?", "What is a dict?"],
        "answers":   ["An ordered collection", "A key-value mapping"],
        "tags":      ["python", "basics"]
      }
    }
    ```
    """

    # 1. Create the deck (AnkiConnect is idempotent — existing decks are reused)
    deck_id = anki_invoke("createDeck", deck=request.topic)

    # 2. Build note objects for addNotes
    notes = []
    for question, answer in zip(request.cards.questions, request.cards.answers):
        notes.append({
            "deckName": request.topic,
            "modelName": "Basic",
            "fields": {
                "Front": question,
                "Back": answer,
            },
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
            },
            "tags": request.cards.tags,
        })

    # 3. Add all notes in a single batch call
    result = anki_request("addNotes", notes=notes)

    # addNotes returns a list of note IDs; null entries mean that card failed
    note_ids_raw = result["result"] if result["result"] is not None else []
    anki_error = result["error"]

    note_ids: list[Optional[int]] = []
    errors: list[str] = []

    if anki_error is not None:
        # Global error — no cards were created
        raise HTTPException(status_code=400, detail=f"AnkiConnect error: {anki_error}")

    for i, nid in enumerate(note_ids_raw):
        note_ids.append(nid)
        if nid is None:
            errors.append(
                f"Card {i + 1} ('{request.cards.questions[i][:50]}...') was not created "
                "(possibly a duplicate)"
            )

    cards_created = sum(1 for nid in note_ids if nid is not None)

    return DeckResponse(
        status="success" if cards_created > 0 else "no_cards_created",
        deck_id=deck_id,
        cards_created=cards_created,
        note_ids=note_ids,
        errors=errors,
    )
