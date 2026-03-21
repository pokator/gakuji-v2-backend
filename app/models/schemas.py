from pydantic import BaseModel
from typing import List, Dict, Any, Tuple, Optional


class LyricsRequest(BaseModel):
    lyrics: str


class EditLyricsRequest(BaseModel):
    original_lyrics: str
    modified_lyrics: str


class UpdateLyricsResponse(BaseModel):
    deleted: int
    inserted: int
    failed: int = 0
    details: Optional[List[Dict[str, Any]]] = None


class LyricsResponse(BaseModel):
    lyrics_lines: List[List[str]]
    word_map: Dict[str, Any]
    kanji_data: Dict[str, Any]
    translated_lines: List[Tuple[str, str]]


class KanjiData(BaseModel):
    jlpt_new: Optional[int] = None
    meanings: Optional[List[str]] = None
    readings_on: Optional[List[str]] = None
    readings_kun: Optional[List[str]] = None
    radicals: Optional[Any] = None


class KanjiResponse(BaseModel):
    kanji: str
    data: Optional[KanjiData]


class Definition(BaseModel):
    pos: Optional[List[str]] = None
    definition: List[str]


class WordEntry(BaseModel):
    idseq: int
    word: str
    furigana: str
    definitions: List[Definition]


# ============ Anki Integration Schemas ============

class KanjiDefinition(BaseModel):
    """Schema for kanji data to be added to Anki."""
    kanji: str
    onyomi: List[str]
    kunyomi: List[str]
    definitions: List[str]
    radicals: Optional[str] = None
    jlpt_level: Optional[str] = None


class KanjiInWord(BaseModel):
    """Kanji referenced within a word."""
    kanji: str
    onyomi: List[str]
    kunyomi: List[str]
    meanings: List[str]


class WordDefinition(BaseModel):
    """Schema for word data to be added to Anki."""
    word: str
    furigana: str
    definitions: List[str]
    kanji_in_word: Optional[List[KanjiInWord]] = None


class AnkiModel(BaseModel):
    """Schema for Anki note model metadata."""
    name: str
    field_names: List[str]
    template_names: Optional[List[str]] = None


class AnkiDeck(BaseModel):
    """Schema for Anki deck metadata."""
    name: str


class AddWordsRequest(BaseModel):
    """Request to add words to Anki deck."""
    deck_name: str
    words: List[WordDefinition]
    model_name: str = "Word"
    field_mapping: Optional[Dict[str, str]] = None


class AddKanjiRequest(BaseModel):
    """Request to add kanji to Anki deck."""
    deck_name: str
    kanji: List[KanjiDefinition]
    model_name: str = "Kanji"
    field_mapping: Optional[Dict[str, str]] = None


class AnkiBatchResponse(BaseModel):
    """Response from batch Anki operations."""
    success_count: int
    failed_count: int
    duplicates_skipped: int = 0
    error_details: Optional[List[Dict[str, Any]]] = None


class CreateDeckRequest(BaseModel):
    """Request to create a deck in Anki."""
    deck_name: str


class WordResponse(BaseModel):
    idseq: int
    word_info: WordEntry