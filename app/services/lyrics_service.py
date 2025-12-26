from pathlib import Path
import os
import logging
import deepl
from jamdict import Jamdict
from janome.tokenizer import Tokenizer
from typing import List, Dict, Any, Tuple, cast
from supabase import create_client, Client
from app.config import settings
from app.utils.text_processing import load_kanji_data, extract_unicode_block, CONST_KANJI, is_japanese

# Initialize expensive resources
deepl_client = deepl.DeepLClient(settings.deepl_key)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Check for database in volume first (Railway production)
volume_db_path = Path("/jamdict_data/storage/jamdict.db")
app_db_path = PROJECT_ROOT / "jamdict_data" / "jamdict.db"

if volume_db_path.exists():
    db_path = volume_db_path
else:
    # Fall back to local development path
    db_path = app_db_path

jam = Jamdict(db_file=str(db_path))
print(f"\n✓ Jamdict initialized successfully with: {db_path}", flush=True)
t = Tokenizer()
supabase_client: Client = create_client(settings.supabase_url, settings.supabase_key)

# Load kanji data
kanji_data: Dict[str, Any] = load_kanji_data('kanji.json')

def get_kanji_data(kanji: str) -> Any:
    if kanji in kanji_data:
        data = kanji_data[kanji]
        radicals = jam.krad[kanji]
        sending_data = {
            "jlpt_new": data["jlpt_new"],
            "meanings": data["meanings"],
            "readings_on": data["readings_on"],
            "readings_kun": data["readings_kun"],
            "radicals": radicals
        }
        return sending_data
    else:
        return None

def get_all_kanji_data(kanji_list: List[str]) -> Dict[str, Any]:
    all_kanji_data: Dict[str, Any] = {}
    for kanji in kanji_list:
        data = get_kanji_data(kanji)
        all_kanji_data[kanji] = data
    return all_kanji_data

def tokenize_line(line: str) -> List[Tuple[str, Any]]:
    tokens = t.tokenize(line)
    result: List[Tuple[str, Any]] = []
    for token in tokens:
        base_form = token.base_form # type: ignore
        if base_form == '*':
            base_form = token.surface # type: ignore
        result.append((token.surface, token)) # type: ignore
    return result

def get_word_info(word: str, type: str = "word") -> List[Dict[str, Any]]:
    if type == "not_japanese":
        word_info: List[Dict[str, Any]] = []
        entry_result = {
            "idseq": "",
            "word": word,
            "furigana": "",
            "definitions": [{"pos": ["Not Japanese"], "definition": ["Not a Japanese word"]}]
        }
        word_info.append(entry_result)
        return word_info
    
    try:
        result = jam.lookup(word)
    except Exception:
        return []
    word_info: List[Dict[str, Any]] = []
    for entry in result.entries: 
        common = False
        if type == "particle" and not ("conjunction" in entry.senses[0].pos or "particle" in entry.senses[0].pos):
            continue
        for kanji in entry.kanji_forms:
            if kanji.text == word and kanji.pri and "news1" in kanji.pri:
                common = True
                break
        idseq = entry.idseq
        if entry.kanji_forms:
            word_text = entry.kanji_forms[0].text
        else:
            word_text = entry.kana_forms[0].text
        furigana = entry.kana_forms[0].text
        word_properties: List[Dict[str, Any]] = []
        
        for sense in entry.senses[:3]:
            pos = sense.pos
            definition = [sense_gloss.text for sense_gloss in sense.gloss]
            word_properties.append({
                "pos": pos,
                "definition": definition
            })

        entry_result = {
            "idseq": idseq,
            "word": word_text,
            "furigana": furigana,
            "definitions": word_properties
        }
        
        if common:
            word_info.insert(0, entry_result)
        else:
            word_info.append(entry_result)
    return word_info[:4]

def process_tokenized_line(line: List[Tuple[str, Any]], word_map: Dict[str, Any]) -> List[str]:
    lyric_line: List[str] = []
    i: int = 0
    while i < len(line):
        surface, token = line[i]

        if surface in word_map:
            lyric_line.append(surface)
            i += 1
            continue

        if not is_japanese(surface):
            word_info = get_word_info(surface, type="not_japanese")
            word_map[surface] = word_info
            lyric_line.append(surface)
            i += 1
            continue
        
        # case when token is a particle
        if token and "助詞" in token.part_of_speech:
            lyric_line.append(surface)
            if surface not in word_map:
                word_info = get_word_info(surface, type="particle")
                word_map[surface] = word_info
            i += 1
            continue

        combined_surface = surface
        word_info = get_word_info(token.base_form)
        j = i + 1

        while j < len(line):
            next_surface, next_token = line[j]
            if not is_japanese(next_surface):
                break
            
            # consider the case where the next token is a particle
            if next_token and "助詞" in next_token.part_of_speech:
                break

            net_surface = combined_surface + next_surface
            next_word_info = get_word_info(net_surface)

            if next_word_info:
                word_info = next_word_info
                combined_surface = net_surface
                j += 1
            else:
                break

        lyric_line.append(combined_surface)

        if combined_surface not in word_map:
            word_map[combined_surface] = word_info

        i = j
                
    return lyric_line

def translate_lyrics_lines(lyric_lines: List[List[str]]) -> List[Tuple[str, str]]:
    print("Translating lyrics...")
    translated_lines: List[Tuple[str, str]] = []
    for line in lyric_lines:
        joined_line = ''.join(line)
        if not line or not is_japanese(joined_line):
            translated_lines.append((joined_line, joined_line))
            continue
        
        if joined_line in [pair[0] for pair in translated_lines]:
            translated_lines.append(next(pair for pair in translated_lines if pair[0] == joined_line))
            continue
        result = deepl_client.translate_text(joined_line, source_lang="JA", target_lang="EN-US")
        translated_lines.append((joined_line, result.text)) # type: ignore
    return translated_lines

def process_lyrics(lyrics: str) -> Tuple[List[List[str]], Dict[str, Any], Dict[str, Any], List[Tuple[str, str]]]:
    from app.utils.text_processing import dakuten_check  # import here to avoid circular
    lines = lyrics.split('\n')
    lines = dakuten_check(lines)
    tokenized_lines = [tokenize_line(line) for line in lines]
    
    word_map: Dict[str, Any] = {}
    lyric_lines: List[List[str]] = []
    translated_lines: List[Tuple[str, str]] = []
    for i, (line, tokenized_line) in enumerate(zip(lines, tokenized_lines)):
        joined_line = ''.join([surface for surface, _ in tokenized_line])
        db_data = get_line_from_db(joined_line)
        if db_data:
            translation, tokens_list = db_data
            translated_lines.append((joined_line, translation))
            lyric_line = [token['token'] for token in tokens_list]
            lyric_lines.append(lyric_line)
            for token in tokens_list:
                word = token['token']
                idseqs = token['idseqs']
                word_info = get_word_info_from_idseqs(idseqs)
                word_map[word] = word_info
        else:
            lyric_line = process_tokenized_line(tokenized_line, word_map)
            lyric_lines.append(lyric_line)
            if not lyric_line or not is_japanese(joined_line):
                translation = joined_line
            else:
                result = deepl_client.translate_text(joined_line, source_lang="JA", target_lang="EN-US")
                translation = result.text  # type: ignore
            translated_lines.append((joined_line, translation))
            # prepare tokens_list
            tokens_list = []
            for word in lyric_line:
                if word in word_map and word_map[word]:
                    # filter out empty/None idseq values and normalize to strings
                    idseqs = [str(entry.get('idseq')).strip() for entry in word_map[word] if str(entry.get('idseq')).strip()]
                    tokens_list.append({'token': word, 'idseqs': idseqs})
            # insert
            supabase_client.table('lines').insert({'line': joined_line, 'translation': translation, 'tokens': tokens_list}).execute()
    
    kanji_list = extract_unicode_block(CONST_KANJI, lyrics)
    kanji_list = list(set(kanji_list))
    kanji_data_dict = get_all_kanji_data(kanji_list)
    
    return lyric_lines, word_map, kanji_data_dict, translated_lines

def get_kanji_count() -> int:
    return len(kanji_data)

def get_line_from_db(line: str) -> Tuple[str, List[Dict[str, Any]]] | None:
    response = supabase_client.table('lines').select('translation, tokens').eq('line', line).execute()
    if response.data:
        data = cast(Dict[str, Any], response.data[0])
        translation = cast(str, data['translation'])
        tokens = cast(List[Dict[str, Any]], data['tokens'])
        return translation, tokens
    return None


def sync_lyrics_lines(original_lyrics: str, modified_lyrics: str) -> Tuple[List[List[str]], Dict[str, Any], Dict[str, Any], List[Tuple[str, str]]]:
    """Compare original and modified lyrics line-by-line and apply deletes/inserts to Supabase.

    This implementation performs client-side delete+insert operations. It assumes `line` is
    the primary key in the `lines` table.
    """
    from app.utils.text_processing import dakuten_check
    import difflib

    deleted = 0
    inserted = 0
    failed = 0
    details: List[Dict[str, Any]] = []

    orig_lines = original_lyrics.split('\n') if original_lyrics else []
    mod_lines = modified_lyrics.split('\n') if modified_lyrics else []
    orig_lines = dakuten_check(orig_lines)
    mod_lines = dakuten_check(mod_lines)

    matcher = difflib.SequenceMatcher(None, orig_lines, mod_lines)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        # delete/replace -> remove old lines
        if tag in ("delete", "replace"):
            for old_line in orig_lines[i1:i2]:
                try:
                    supabase_client.table('lines').delete().eq('line', old_line).execute()
                    deleted += 1
                except Exception as e:
                    failed += 1
                    details.append({"op": "delete", "line": old_line, "error": str(e)})

        # insert/replace -> insert new lines
        if tag in ("insert", "replace"):
            for new_line in mod_lines[j1:j2]:
                try:
                    # if it already exists, skip
                    if get_line_from_db(new_line):
                        continue

                    tokenized = tokenize_line(new_line)
                    word_map: Dict[str, Any] = {}
                    lyric_line = process_tokenized_line(tokenized, word_map)
                    joined_line = ''.join([surface for surface, _ in tokenized])

                    if not lyric_line or not is_japanese(joined_line):
                        translation = joined_line
                    else:
                        result = deepl_client.translate_text(joined_line, source_lang="JA", target_lang="EN-US")
                        translation = result.text  # type: ignore

                    tokens_list: List[Dict[str, Any]] = []
                    for word in lyric_line:
                        if word in word_map and word_map[word]:
                            idseqs = [str(entry.get('idseq')).strip() for entry in word_map[word] if str(entry.get('idseq')).strip()]
                            tokens_list.append({'token': word, 'idseqs': idseqs})

                    supabase_client.table('lines').insert({'line': joined_line, 'translation': translation, 'tokens': tokens_list}).execute()
                    inserted += 1
                except Exception as e:
                    failed += 1
                    details.append({"op": "insert", "line": new_line, "error": str(e)})

    # After applying DB changes, return the processed representation of the modified lyrics
    lyric_lines, word_map, kanji_data_dict, translated_lines = process_lyrics(modified_lyrics)
    return lyric_lines, word_map, kanji_data_dict, translated_lines

def get_word_info_from_idseq(idseq: str) -> Dict[str, Any] | None:
    result = jam.lookup(idseq)
    for entry in result.entries:
        common = False
        for kanji in entry.kanji_forms:
            if kanji.pri and "news1" in kanji.pri:
                common = True
                break
        idseq_val = entry.idseq
        if entry.kanji_forms:
            word_text = entry.kanji_forms[0].text
        else:
            word_text = entry.kana_forms[0].text
        furigana = entry.kana_forms[0].text
        word_properties = []
        for sense in entry.senses[:3]:
            pos = sense.pos
            definition = [sense_gloss.text for sense_gloss in sense.gloss]
            word_properties.append({
                "pos": pos,
                "definition": definition
            })
        entry_result = {
            "idseq": idseq_val,
            "word": word_text,
            "furigana": furigana,
            "definitions": word_properties
        }
        return entry_result
    return None



def get_word_info_from_idseqs(idseqs: List[int]) -> List[Dict[str, Any]]:
    word_info = []
    for idseq in idseqs:
        # Ensure we don't pass empty or invalid idseq values to jam.lookup
        if idseq is None:
            continue
        idseq_str = str(idseq).strip()
        if not idseq_str:
            continue
        id = "id#" + idseq_str
        try:
            entry_result = get_word_info_from_idseq(id)
        except ValueError:
            # jam.lookup or downstream code may raise ValueError when id is malformed
            continue
        if entry_result:
            word_info.append(entry_result)
    return word_info[:4] 