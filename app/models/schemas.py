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


class WordResponse(BaseModel):
    idseq: int
    word_info: WordEntry