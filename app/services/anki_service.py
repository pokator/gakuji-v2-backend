import httpx
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from app.config import settings
from app.exceptions import AnkiConnectError
from app.models.schemas import (
    WordDefinition,
    KanjiDefinition,
    AddWordsRequest,
    AddKanjiRequest,
    AnkiBatchResponse,
)

logger = logging.getLogger(__name__)

# app/anki_models.py

WORD_MODEL = {
    "name": "Gakuji Word",
    "fields": ["Word", "Furigana", "Definitions", "Kanji"],
    "css": """
        .card {
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 5vw;
            max-width: 600px;
            margin: 0 auto;
            box-sizing: border-box;
        }

        /* Front */
        .word-front {
            font-size: clamp(48px, 12vw, 96px);
            font-weight: bold;
        }

        /* Back */
        .furigana {
            font-size: clamp(24px, 6vw, 40px);
            margin-bottom: 12px;
        }
        .definitions {
            font-size: clamp(14px, 3.5vw, 20px);
            margin: 10px 0;
            line-height: 1.5;
        }
        .kanji-block {
            display: flex;
            flex-wrap: wrap;
            gap: clamp(4px, 2vw, 10px);
            justify-content: center;
            margin-top: 16px;
        }
        .kanji-item {
            border: 1px solid #ccc;
            border-radius: 6px;
            padding: clamp(4px, 2vw, 8px) clamp(6px, 2.5vw, 12px);
            flex: 1 1 clamp(80px, 25%, 140px);
        }
        .kanji-char {
            font-size: clamp(20px, 6vw, 36px);
            font-weight: bold;
            display: block;
        }
        .kanji-readings {
            font-size: clamp(10px, 2.5vw, 14px);
        }
    """,
    "templates": [{
        "Name": "Word Card",
        "Front": "<div class='word-front'>{{Word}}</div>",
        "Back": """
            <div class='furigana'>{{Furigana}}</div>
            <hr>
            <div class='definitions'>{{Definitions}}</div>
            {{#Kanji}}<div class='kanji-block'>{{Kanji}}</div>{{/Kanji}}
        """,
    }],
}

KANJI_MODEL = {
    "name": "Gakuji Kanji",
    "fields": ["Kanji", "Onyomi", "Kunyomi", "Definitions", "Radicals", "JLPT"],
    "css": """
        .card {
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 5vw;
            max-width: 600px;
            margin: 0 auto;
            box-sizing: border-box;
        }

        /* Front */
        .kanji-front {
            font-size: clamp(80px, 20vw, 160px);
            font-weight: bold;
            line-height: 1;
        }

        /* Back */
        .kanji-main {
            font-size: clamp(48px, 12vw, 96px);
            font-weight: bold;
            line-height: 1;
        }
        .readings {
            font-size: clamp(14px, 3.5vw, 20px);
            margin: 8px 0;
        }
        .definitions {
            font-size: clamp(14px, 3.5vw, 20px);
            margin: 10px 0;
            line-height: 1.5;
        }
        .radicals {
            font-size: clamp(12px, 3vw, 16px);
            margin-top: 10px;
        }
        .jlpt {
            display: inline-block;
            margin-top: 10px;
            padding: clamp(2px, 1vw, 4px) clamp(6px, 2vw, 12px);
            border-radius: 4px;
            font-size: clamp(11px, 3vw, 15px);
        }
    """,
    "templates": [{
        "Name": "Kanji Card",
        "Front": "<div class='kanji-front'>{{Kanji}}</div>",
        "Back": """
            <div class='kanji-main'>{{Kanji}}</div>
            <hr>
            <div class='readings'>音: {{Onyomi}}</div>
            <div class='readings'>訓: {{Kunyomi}}</div>
            <div class='definitions'>{{Definitions}}</div>
            {{#Radicals}}<div class='radicals'> radicals: {{Radicals}}</div>{{/Radicals}}
            {{#JLPT}}<div class='jlpt'>JLPT {{JLPT}}</div>{{/JLPT}}
        """,
    }],
}

ALL_MODELS = [WORD_MODEL, KANJI_MODEL]


class AnkiConnectClient:
    """Client for interacting with AnkiConnect add-on."""

    def __init__(self, url: str = None, timeout: int = None):
        self.url = url or settings.anki_connect_url
        self.timeout = timeout or settings.anki_connect_timeout
        self.version = 6

    async def invoke(self, action: str, params: Dict[str, Any] = None) -> Any:
        """
        Invoke an AnkiConnect action with error handling and timeout.

        Args:
            action: The AnkiConnect action to invoke
            params: Parameters for the action

        Returns:
            The result from AnkiConnect

        Raises:
            AnkiConnectError: If the action fails or times out
        """
        if params is None:
            params = {}

        request_body = {
            "action": action,
            "version": self.version,
            "params": params,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.url, json=request_body)
                response.raise_for_status()
                result = response.json()

                # Check for AnkiConnect error response
                if result.get("error") is not None:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"AnkiConnect error for action '{action}': {error_msg}")
                    raise AnkiConnectError(f"AnkiConnect error: {error_msg}")

                return result.get("result")

        except httpx.TimeoutException as e:
            msg = f"AnkiConnect request timed out after {self.timeout}s"
            logger.error(msg)
            raise AnkiConnectError(msg) from e
        except httpx.ConnectError as e:
            msg = f"Failed to connect to AnkiConnect at {self.url}"
            logger.error(msg)
            raise AnkiConnectError(msg) from e
        except httpx.HTTPStatusError as e:
            msg = f"AnkiConnect returned HTTP {e.response.status_code}"
            logger.error(msg)
            raise AnkiConnectError(msg) from e
        except Exception as e:
            msg = f"Unexpected error communicating with AnkiConnect: {str(e)}"
            logger.error(msg)
            raise AnkiConnectError(msg) from e

    async def get_model_names(self) -> List[str]:
        """Get list of available note model names."""
        return await self.invoke("modelNames")

    async def get_model_field_names(self, model_name: str) -> List[str]:
        """Get field names for a specific model."""
        return await self.invoke("modelFieldNames", {"modelName": model_name})
    
    async def create_model(
    self,
    model_name: str,
    fields: List[str],
    card_templates: List[Dict[str, str]],
    css: str = "",
    ) -> None:
        """Create a new note model."""
        await self.invoke("createModel", {
            "modelName": model_name,
            "inOrderFields": fields,
            "css": css,
            "cardTemplates": card_templates,
        })

    async def get_deck_names(self) -> List[str]:
        """Get list of available deck names."""
        return await self.invoke("deckNames")

    async def create_deck(self, deck_name: str) -> int:
        """
        Create a deck (idempotent — returns deck ID even if it already exists).

        Args:
            deck_name: Name of the deck to create

        Returns:
            The deck ID
        """
        return await self.invoke("createDeck", {"deck": deck_name})

    async def check_valid_model(
        self, model_name: str, required_fields: List[str]
    ) -> bool:
        """
        Validate that a model exists and has all required fields.

        Args:
            model_name: Name of the model
            required_fields: List of field names that must exist

        Returns:
            True if valid

        Raises:
            AnkiConnectError: If model doesn't exist or is missing required fields
        """
        try:
            available_models = await self.get_model_names()
            if model_name not in available_models:
                raise AnkiConnectError(
                    f"Model '{model_name}' not found. Available models: {available_models}"
                )

            field_names = await self.get_model_field_names(model_name)
            missing_fields = set(required_fields) - set(field_names)
            if missing_fields:
                raise AnkiConnectError(
                    f"Model '{model_name}' missing required fields: {missing_fields}. "
                    f"Available fields: {field_names}"
                )

            return True
        except AnkiConnectError:
            raise
        except Exception as e:
            raise AnkiConnectError(f"Error validating model '{model_name}': {str(e)}")
        
    async def find_notes(self, query: str) -> List[int]:
        """Find note IDs matching an Anki search query."""
        return await self.invoke("findNotes", {"query": query})

    async def notes_info(self, note_ids: List[int]) -> List[Dict[str, Any]]:
        """Get full note data for a list of note IDs."""
        return await self.invoke("notesInfo", {"notes": note_ids})

    async def add_notes(
        self, deck_name: str, notes: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Add multiple notes to a deck (all-or-nothing behavior).

        Args:
            deck_name: Name of the deck
            notes: List of note dictionaries

        Returns:
            List of note IDs for successfully added notes

        Raises:
            AnkiConnectError: If any note fails to add
        """
        if not notes:
            return []

        params = {
            "notes": [
                {
                    "deckName": deck_name,
                    **note,  # Spread note properties (model, fields, tags, etc.)
                }
                for note in notes
            ]
        }

        try:
            result = await self.invoke("addNotes", params)
            # Check if any notes failed (AnkiConnect returns None for failed notes)
            if result and None in result:
                failed_count = result.count(None)
                raise AnkiConnectError(
                    f"Failed to add {failed_count} out of {len(notes)} notes. "
                    "All notes rejected (all-or-nothing behavior)."
                )
            return result
        except AnkiConnectError:
            raise
        except Exception as e:
            raise AnkiConnectError(f"Error adding notes: {str(e)}")

async def ensure_model(client: AnkiConnectClient, model_def: dict) -> None:
    """Create a model if it doesn't already exist."""
    existing = await client.get_model_names()
    if model_def["name"] not in existing:
        logger.info(f"Creating model '{model_def['name']}'")
        await client.create_model(
            model_name=model_def["name"],
            fields=model_def["fields"],
            card_templates=model_def["templates"],
            css=model_def.get("css", ""),
        )
    else:
        logger.info(f"Model '{model_def['name']}' already exists, skipping")


async def get_existing_first_fields_in_deck(
    client: AnkiConnectClient, deck_name: str
) -> set[str]:
    """Return a set of first-field values for all notes in the deck."""
    note_ids = await client.find_notes(f'deck:"{deck_name}"')
    if not note_ids:
        return set()
    notes_data = await client.notes_info(note_ids)
    return {
        list(note["fields"].values())[0]["value"]
        for note in notes_data
    }



async def setup_and_add_words(
    deck_name: str,
    words: List[WordDefinition],
) -> AnkiBatchResponse:
    """
    Full flow: ensure model → ensure deck → check existing → add new notes only.
    """
    client = AnkiConnectClient()

    # 1. Ensure the model exists
    await ensure_model(client, WORD_MODEL)

    # 2. Ensure the deck exists (idempotent)
    await client.create_deck(deck_name)

    # 3. Fetch words already in this deck from Anki
    existing_words = await get_existing_first_fields_in_deck(client, deck_name)
    logger.info(f"Found {len(existing_words)} existing notes in deck '{deck_name}'")

    # 4. Filter out duplicates — both within the batch AND against Anki
    seen: set[str] = set()
    new_words: List[WordDefinition] = []
    duplicates_skipped = 0

    for word_def in words:
        if word_def.word in existing_words or word_def.word in seen:
            duplicates_skipped += 1
            logger.info(f"Skipping duplicate: {word_def.word}")
        else:
            seen.add(word_def.word)
            new_words.append(word_def)

    if not new_words:
        return AnkiBatchResponse(
            success_count=0,
            failed_count=0,
            duplicates_skipped=duplicates_skipped,
        )

    # 5. Build and add notes
    def format_kanji_in_word_html(kanji_list) -> str:
        items = []
        for k in (kanji_list or [])[:6]:
            onyomi  = "、".join(k.onyomi)  if k.onyomi  else "—"
            kunyomi = "、".join(k.kunyomi) if k.kunyomi else "—"
            meanings = ", ".join(k.meanings) if k.meanings else ""
            items.append(f"""
                <div class='kanji-item'>
                    <span class='kanji-char'>{k.kanji}</span>
                    <span class='kanji-readings'>音: {onyomi} / 訓: {kunyomi}</span>
                    <div>{meanings}</div>
                </div>
            """)
        return "".join(items)

    notes = [
        {
            "modelName": WORD_MODEL["name"],
            "fields": {
                "Word": w.word,
                "Furigana": w.furigana,
                "Definitions": "; ".join(w.definitions) if isinstance(w.definitions, list) else (w.definitions or ""),
                "Kanji": format_kanji_in_word_html(w.kanji_in_word),
            },
            "tags": ["from-gakuji"],
        }
        for w in new_words
    ]

    note_ids = await client.add_notes(deck_name, notes)
    return AnkiBatchResponse(
        success_count=len(note_ids),
        failed_count=0,
        duplicates_skipped=duplicates_skipped,
    )

async def setup_and_add_kanji(
    deck_name: str,
    kanji: List[KanjiDefinition],
) -> AnkiBatchResponse:
    """
    Full flow: ensure model → ensure deck → check existing → add new notes only.
    """
    client = AnkiConnectClient()

    # 1. Ensure the model exists
    await ensure_model(client, KANJI_MODEL)

    # 2. Ensure the deck exists (idempotent)
    await client.create_deck(deck_name)

    # 3. Fetch kanji already in this deck from Anki
    existing_kanji = await get_existing_first_fields_in_deck(client, deck_name)
    logger.info(f"Found {len(existing_kanji)} existing notes in deck '{deck_name}'")

    # 4. Filter out duplicates — both within the batch AND against Anki
    seen: set[str] = set()
    new_kanji: List[KanjiDefinition] = []
    duplicates_skipped = 0

    for kanji_def in kanji:
        if kanji_def.kanji in existing_kanji or kanji_def.kanji in seen:
            duplicates_skipped += 1
            logger.info(f"Skipping duplicate: {kanji_def.kanji}")
        else:
            seen.add(kanji_def.kanji)
            new_kanji.append(kanji_def)

    if not new_kanji:
        return AnkiBatchResponse(
            success_count=0,
            failed_count=0,
            duplicates_skipped=duplicates_skipped,
        )

    # 5. Build and add notes
    notes = [
        {
            "modelName": KANJI_MODEL["name"],
            "fields": {
                "Kanji": k.kanji,
                "Onyomi": "; ".join(k.onyomi) if isinstance(k.onyomi, list) else (k.onyomi or ""),
                "Kunyomi": "; ".join(k.kunyomi) if isinstance(k.kunyomi, list) else (k.kunyomi or ""),
                "Definitions": "; ".join(k.definitions) if isinstance(k.definitions, list) else (k.definitions or ""),
                "Radicals": k.radicals if k.radicals else "",
                "JLPT": k.jlpt_level if k.jlpt_level is not None else "",
            },
            "tags": ["from-gakuji"],
        }
        for k in new_kanji
    ]

    note_ids = await client.add_notes(deck_name, notes)
    return AnkiBatchResponse(
        success_count=len(note_ids),
        failed_count=0,
        duplicates_skipped=duplicates_skipped,
    )