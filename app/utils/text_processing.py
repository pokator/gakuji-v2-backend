import json
import re
from typing import List, Dict, Any

# Mapping of basic hiragana/katakana to their dakuten and handakuten equivalents
DAKUTEN_MAP: Dict[str, str] = {
    'か': 'が', 'き': 'ぎ', 'く': 'ぐ', 'け': 'げ', 'こ': 'ご',
    'さ': 'ざ', 'し': 'じ', 'す': 'ず', 'せ': 'ぜ', 'そ': 'ぞ',
    'た': 'だ', 'ち': 'ぢ', 'つ': 'づ', 'て': 'で', 'と': 'ど',
    'は': 'ば', 'ひ': 'び', 'ふ': 'ぶ', 'へ': 'べ', 'ほ': 'ぼ',
    'ハ': 'バ', 'ヒ': 'ビ', 'フ': 'ブ', 'ヘ': 'ベ', 'ホ': 'ボ',
    'カ': 'ガ', 'キ': 'ギ', 'ク': 'グ', 'ケ': 'ゲ', 'コ': 'ゴ',
    'サ': 'ザ', 'シ': 'ジ', 'ス': 'ズ', 'セ': 'ゼ', 'ソ': 'ゾ',
    'タ': 'ダ', 'チ': 'ヂ', 'ツ': 'ヅ', 'テ': 'デ', 'ト': 'ド',
}

HANDAKUTEN_MAP: Dict[str, str] = {
    'は': 'ぱ', 'ひ': 'ぴ', 'ふ': 'ぷ', 'へ': 'ぺ', 'ほ': 'ぽ',
    'ハ': 'パ', 'ヒ': 'ピ', 'フ': 'プ', 'ヘ': 'ペ', 'ホ': 'ポ'
}

CONST_KANJI: str = r'[㐀-䶵一-鿋豈-頻]'
HIRAGANA_FULL: str = r'[ぁ-ゟ]'
KATAKANA_FULL: str = r'[゠-ヿ]'
ALL_JAPANESE: str = f'{CONST_KANJI}|{HIRAGANA_FULL}|{KATAKANA_FULL}'

def load_kanji_data(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def dakuten_check(lines: List[str]) -> List[str]:
    result: List[str] = []
    for line in lines:
        new_line = process_dakuten_handakuten(line)
        result.append(new_line)
    return result

def process_dakuten_handakuten(text: str) -> str:
    result: List[str] = []
    chars: List[str] = list(text)
    i: int = 0
    
    while i < len(chars):
        if i < len(chars) - 1:
            current_char = chars[i]
            next_char = chars[i + 1]
            
            if next_char == '゙':  # Dakuten mark
                if current_char in DAKUTEN_MAP:
                    result.append(DAKUTEN_MAP[current_char])
                    i += 2
                else:
                    result.append(current_char)
                    result.append(next_char)
                    i += 2
            elif next_char == '゚':  # Handakuten mark
                if current_char in HANDAKUTEN_MAP:
                    result.append(HANDAKUTEN_MAP[current_char])
                    i += 2
                else:
                    result.append(current_char)
                    result.append(next_char)
                    i += 2
            else:
                result.append(current_char)
                i += 1
        else:
            result.append(chars[i])
            i += 1
            
    return ''.join(result)

def extract_unicode_block(unicode_block: str, string: str) -> List[str]:
    return re.findall(unicode_block, string)

def is_japanese(text: str) -> bool:
    return bool(re.match(r'[぀-ヿ一-鿿＀-￯]', text))