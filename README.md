# Anki Flashcard Generator API and n8n Integration

A FastAPI service that creates Anki decks and Basic (Front/Back) flashcards via [AnkiConnect](https://git.sr.ht/~foosoft/anki-connect).

## Prerequisites

1. **Anki** desktop app installed and running
2. **AnkiConnect** add-on installed (Tools → Add-ons → Get Add-ons → code `2055492159`)
  - Anki Download Link (https://apps.ankiweb.net/)
  - The Anki desktop must be open on your device for the flashcard generator to work.
3. Docker (https://www.docker.com/)

## Setup (Docker)

```bash
docker compose up
```

## Environment Variable Integration (TODO)

## Endpoints

### `GET /health`

Verify AnkiConnect is reachable.

### `POST /create-deck`

Create a deck and add flashcards.

**Request:**

```json
{
  "topic": "Python Basics",
  "cards": {
    "questions": [
      "What is a list?",
      "What is a dict?"
    ],
    "answers": [
      "An ordered, mutable collection of items",
      "A key-value mapping data structure"
    ],
    "tags": ["python", "basics"]
  }
}
```

**Response:**

```json
{
  "status": "success",
  "deck_id": 1234567890,
  "cards_created": 2,
  "note_ids": [1716968687679, 1716968687680],
  "errors": []
}
```

### Validation Rules

- `questions` and `answers` arrays **must** be the same length (returns 422 if mismatched)
- `topic` must not be empty
- At least one question/answer pair is required
- Duplicate cards within the same deck are skipped (reported in `errors`)

## Interactive Docs

Once running, visit `http://localhost:8000/docs` for Swagger UI.

## Example: curl

```bash
curl -X POST http://localhost:8000/create-deck \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AWS Solutions Architect",
    "cards": {
      "questions": ["What is an S3 bucket?", "What does IAM stand for?"],
      "answers": ["Object storage service", "Identity and Access Management"],
      "tags": ["aws", "cloud"]
    }
  }'
```

### Using cloudfare tunneling for n8n interaction

cloudflared tunnel --url http://localhost:8000

grab the tunneling url and paste it into the url for http, create anki cards node, requests on n8n