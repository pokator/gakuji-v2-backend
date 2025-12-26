from fastapi import APIRouter, HTTPException, Request
from app.models.schemas import (
    LyricsRequest,
    LyricsResponse,
    EditLyricsRequest,
    UpdateLyricsResponse,
    KanjiResponse,
    WordResponse,
)
from app.services.lyrics_service import process_lyrics, get_kanji_data, get_word_info_from_idseqs, sync_lyrics_lines
import logging

router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/")
async def root():
    return {
        "message": "Japanese Lyrics Processor API",
        "endpoints": {
            "/process-lyrics": "POST - Process Japanese lyrics",
            "/health": "GET - Health check",
            "/kanji/{kanji}": "GET - Lookup kanji data for a single kanji",
            "/word/{idseq}": "GET - Lookup word info by idseq",
            "/docs": "GET - Interactive API documentation"
        }
    }

@router.get("/health")
async def health_check():
    from app.config import settings
    from app.services.lyrics_service import get_kanji_count
    return {
        "status": "healthy",
        "deepl_api": "connected" if settings.deepl_key else "missing",
        "jamdict": "loaded",
        "kanji_data": f"{get_kanji_count()} kanji loaded"
    }

@router.post("/process-lyrics", response_model=LyricsResponse)
async def process_lyrics_endpoint(request: LyricsRequest):
    try:
        if not request.lyrics or not request.lyrics.strip():
            raise HTTPException(status_code=400, detail="Lyrics cannot be empty")
        
        lyric_lines, word_map, kanji_data_dict, translated_lines = process_lyrics(request.lyrics)
        
        return {
            "lyrics_lines": lyric_lines,
            "word_map": word_map,
            "kanji_data": kanji_data_dict,
            "translated_lines": translated_lines
        }
    except Exception as e:
        logger.error(f"Error processing lyrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing lyrics: {str(e)}")


@router.get("/kanji/{kanji}", response_model=KanjiResponse)
async def lookup_kanji(kanji: str):
    try:
        data = get_kanji_data(kanji)
        if not data:
            raise HTTPException(status_code=404, detail="Kanji not found")
        logger.debug(f"Kanji data for '{kanji}': {data}")
        return {"kanji": kanji, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up kanji '{kanji}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/word/{idseq}", response_model=WordResponse)
async def lookup_word(idseq: int):
    try:
        word_info = get_word_info_from_idseqs([idseq])
        if not word_info:
            raise HTTPException(status_code=404, detail="Word not found")
        # return the first matching entry reconstructed from idseq
        logger.debug(f"Word info for idseq '{idseq}': {word_info}")
        return {"idseq": idseq, "word_info": word_info[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error looking up idseq '{idseq}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-lyrics", response_model=LyricsResponse)
async def sync_lyrics_endpoint(request: EditLyricsRequest):
    try:
        if not request.original_lyrics and not request.modified_lyrics:
            raise HTTPException(status_code=400, detail="Both original and modified lyrics cannot be empty")

        lyric_lines, word_map, kanji_data_dict, translated_lines = sync_lyrics_lines(request.original_lyrics or "", request.modified_lyrics or "")
        return {
            "lyrics_lines": lyric_lines,
            "word_map": word_map,
            "kanji_data": kanji_data_dict,
            "translated_lines": translated_lines,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing lyrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))