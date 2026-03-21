from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    AddWordsRequest,
    AddKanjiRequest,
    AnkiBatchResponse,
    CreateDeckRequest,
)
from app.services.anki_service import (
    AnkiConnectClient,
    setup_and_add_kanji,
    setup_and_add_words,
)
from app.exceptions import AnkiConnectError
import logging

router = APIRouter(prefix="/anki", tags=["anki"])
logger = logging.getLogger(__name__)


@router.get("/models")
async def get_models():
    """List all available Anki note models."""
    try:
        client = AnkiConnectClient()
        models = await client.get_model_names()
        return {"models": models}
    except AnkiConnectError as e:
        logger.error(f"Failed to get models: {str(e)}")
        raise HTTPException(
            status_code=503, detail="Failed to connect to Anki. Is AnkiConnect running?"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting models: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/decks")
async def get_decks():
    """List all available Anki decks."""
    try:
        client = AnkiConnectClient()
        decks = await client.get_deck_names()
        return {"decks": decks}
    except AnkiConnectError as e:
        logger.error(f"Failed to get decks: {str(e)}")
        raise HTTPException(
            status_code=503, detail="Failed to connect to Anki. Is AnkiConnect running?"
        )
    except Exception as e:
        logger.error(f"Unexpected error getting decks: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/decks")
async def create_deck(request: CreateDeckRequest):
    """Create a new deck in Anki (idempotent)."""
    try:
        client = AnkiConnectClient()
        deck_id = await client.create_deck(request.deck_name)
        return {"deck_name": request.deck_name, "deck_id": deck_id}
    except AnkiConnectError as e:
        logger.error(f"Failed to create deck: {str(e)}")
        if "not found" in str(e).lower() or "invalid" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(
            status_code=503, detail="Failed to connect to Anki. Is AnkiConnect running?"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating deck: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/words", response_model=AnkiBatchResponse)
async def add_words(request: AddWordsRequest):
    """Add words to an Anki deck."""
    try:
        result = await setup_and_add_words(
            deck_name=request.deck_name,
            words=request.words,
        )
        return result
    except AnkiConnectError as e:
        error_msg = str(e)
        logger.error(f"Failed to add words: {error_msg}")

        # Determine appropriate HTTP status
        if "not found" in error_msg.lower() or "invalid" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        elif "timeout" in error_msg.lower():
            raise HTTPException(status_code=503, detail=error_msg)
        elif "connect" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="Failed to connect to Anki. Is AnkiConnect running?",
            )
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"Unexpected error adding words: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/kanji", response_model=AnkiBatchResponse)
async def add_kanji(request: AddKanjiRequest):
    """Add kanji to an Anki deck."""
    try:
        result = await setup_and_add_kanji(
            deck_name=request.deck_name,
            kanji=request.kanji,
        )
        return result
    except AnkiConnectError as e:
        error_msg = str(e)
        logger.error(f"Failed to add kanji: {error_msg}")

        if "not found" in error_msg.lower() or "invalid" in error_msg.lower():
            raise HTTPException(status_code=400, detail=error_msg)
        elif "timeout" in error_msg.lower():
            raise HTTPException(status_code=503, detail=error_msg)
        elif "connect" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="Failed to connect to Anki. Is AnkiConnect running?",
            )
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(f"Unexpected error adding kanji: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
