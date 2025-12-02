from janome.tokenizer import Tokenizer
# from janome.analyzer import Analyzer
# import janome.charfilter as charfilter
# import janome.tokenfilter as tokenfilter
from jamdict import Jamdict
import deepl
import json
import os
import re
from dotenv import load_dotenv, dotenv_values

load_dotenv()
config = dotenv_values(".env")
deepl_key = str(config.get("DEEPL_KEY"))
deepl_client = deepl.DeepLClient(deepl_key)

# Mapping of basic hiragana/katakana to their dakuten and handakuten equivalents
DAKUTEN_MAP = {
    # Dakuten cases (濁点)
    'か': 'が', 'き': 'ぎ', 'く': 'ぐ', 'け': 'げ', 'こ': 'ご',
    'さ': 'ざ', 'し': 'じ', 'す': 'ず', 'せ': 'ぜ', 'そ': 'ぞ',
    'た': 'だ', 'ち': 'ぢ', 'つ': 'づ', 'て': 'で', 'と': 'ど',
    'は': 'ば', 'ひ': 'び', 'ふ': 'ぶ', 'へ': 'べ', 'ほ': 'ぼ',
    'ハ': 'バ', 'ヒ': 'ビ', 'フ': 'ブ', 'ヘ': 'ベ', 'ホ': 'ボ',
    'カ': 'ガ', 'キ': 'ギ', 'ク': 'グ', 'ケ': 'ゲ', 'コ': 'ゴ',
    'サ': 'ザ', 'シ': 'ジ', 'ス': 'ズ', 'セ': 'ゼ', 'ソ': 'ゾ',
    'タ': 'ダ', 'チ': 'ヂ', 'ツ': 'ヅ', 'テ': 'デ', 'ト': 'ド',
}

HANDAKUTEN_MAP = {
    # Handakuten cases (半濁点)
    'は': 'ぱ', 'ひ': 'ぴ', 'ふ': 'ぷ', 'へ': 'ぺ', 'ほ': 'ぽ',
    'ハ': 'パ', 'ヒ': 'ピ', 'フ': 'プ', 'ヘ': 'ペ', 'ホ': 'ポ'
}

CONST_KANJI = r'[㐀-䶵一-鿋豈-頻]'
HIRAGANA_FULL = r'[ぁ-ゟ]'
KATAKANA_FULL = r'[゠-ヿ]'
ALL_JAPANESE = f'{CONST_KANJI}|{HIRAGANA_FULL}|{KATAKANA_FULL}'

def load_kanji_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)
kanji_data = load_kanji_data('kanji.json')

# sometimes, the lyrics use the wrong characters for a dakuten'd character. This function checks for that and corrects it.
def dakuten_check(lines):
    result = []
    for line in lines:
        new_line = process_dakuten_handakuten(line)
        result.append(new_line)
    return result

def process_dakuten_handakuten(text: str) -> str:
    """
    Process a string to handle standalone dakuten (゛) and handakuten (゜) marks
    by combining them with the previous character if possible.
    
    Args:
        text: Input string that may contain standalone dakuten/handakuten marks
        
    Returns:
        Processed string with proper dakuten/handakuten combinations
    """
    result = []
    chars = list(text)
    i = 0
    
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

#specifically used to return the list of kanji in the lyrics
def extract_unicode_block(unicode_block, string):
	''' extracts and returns all texts from a unicode block from string argument.
		Note that you must use the unicode blocks defined above, or patterns of similar form '''
	return re.findall( unicode_block, string)

#gets the desired data about a particular kanji contained in the lyrics.
def get_kanji_data(kanji):
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
    
# gets the data for all kanji in the lyrics
def get_all_kanji_data(kanji_list):
    all_kanji_data = {}
    for kanji in kanji_list:
        data = get_kanji_data(kanji)
        all_kanji_data[kanji] = data
    return all_kanji_data

jam = Jamdict(db_file="jamdict_data/jamdict.db")
t = Tokenizer()

# tokenize a line. For each line, return a list of tuples of (surface, token)
def tokenize_line(line):
    tokens = t.tokenize(line)
    result = []
    for token in tokens:
        base_form = token.base_form # type: ignore
        if base_form == '*':
            base_form = token.surface # type: ignore
        result.append((token.surface, token)) # type: ignore
    return result

# dictionary lookups are expensive.
def get_word_info(word, type="word"):
    try:
        result = jam.lookup(word)
    except Exception as e:
        return []
    word_info = []
    for entry in result.entries: 
        common = False
        if type == "particle" and not ("conjunction" in entry.senses[0].pos or "particle" in entry.senses[0].pos):
            continue
        for kanji in entry.kanji_forms:
            #kanji contains text and info
            if kanji.text == word and kanji.pri and "news1" in kanji.pri:
                common = True
                break
        # Limit to 3 entries
        idseq = entry.idseq
        if entry.kanji_forms:
            word_text = entry.kanji_forms[0].text
        else:
            word_text = entry.kana_forms[0].text
        furigana = entry.kana_forms[0].text
        word_properties = []
        
        # limit definitions to 3
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
        
        if(common):
            word_info.insert(0, entry_result)
        else:
            word_info.append(entry_result)
    return word_info[:4]


def is_japanese(text):
    # Regex to match Hiragana, Katakana, Kanji, and Japanese punctuation
    return re.match(r'[぀-ヿ一-鿿＀-￯]', text)

# def process_tokenized_line(line, word_map: dict):
#     lyric_line = []
#     i = 0
#     while i < len(line):
#         surface, token = line[i]

#         if surface in word_map:
#             lyric_line.append(surface)
#             i += 1
#             continue

#         if not is_japanese(surface):
#             lyric_line.append(surface)
#             i += 1
#             continue

#         combined_surface = surface
#         word_info = get_word_info(token.base_form)
#         j = i + 1

#         while j < len(line):
#             next_surface, next_token = line[j]
#             if not is_japanese(next_surface):
#                 break

#             net_surface = combined_surface + next_surface
#             next_word_info = get_word_info(net_surface)

#             if next_word_info:
#                 word_info = next_word_info
#                 combined_surface = net_surface
#                 j += 1
#             else:
#                 break

#         lyric_line.append(combined_surface)

#         if combined_surface not in word_map:
#             word_map[combined_surface] = word_info

#         # move i forward to skip all the consumed tokens
#         i = j
                
#     return lyric_line

def process_tokenized_line(line, word_map: dict):
    lyric_line = []
    i: int = 0
    while i < len(line):
        surface, token = line[i]

        if surface in word_map:
            lyric_line.append(surface)
            i += 1
            continue

        if not is_japanese(surface):
            lyric_line.append(surface)
            i += 1
            continue
        
        # case when token is a particle
        print("Processing token:", surface, token, "extra",  "助詞" in token.part_of_speech)
        if token and token.part_of_speech == "助詞":
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
            if next_token.part_of_speech == "助詞":
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

# want to create a function which translates each line and returns an array of tuples, each tuple containing the original line and the translated line.
def translate_lyrics_lines(lyric_lines: list):
    print("Translating lyrics...", lyric_lines)
    translated_lines = []
    for line in lyric_lines:
        joined_line = ''.join(line)
        if not line or not is_japanese(joined_line):
            translated_lines.append((joined_line, joined_line))
            continue # skip non-japanese lines
        
        if joined_line in [pair[0] for pair in translated_lines]:
            translated_lines.append(next(pair for pair in translated_lines if pair[0] == joined_line))
            continue # already translated
        result = deepl_client.translate_text(joined_line, source_lang="JA", target_lang="EN-US")
        translated_lines.append((joined_line, result.text))  # type: ignore
    return translated_lines


# primary function
def process_lyrics(lyrics: str):
    lines = lyrics.split('\n')
    # first, fix any dakuten/handakuten issues
    lines = dakuten_check(lines)
    # tokenize each line.
    tokenized_lines = [tokenize_line(line) for line in lines]
    
    word_map = {}
    lyric_lines = []
    # for each token, look up in jamdict to get the reading
    for line in tokenized_lines:
        lyric_lines.append(process_tokenized_line(line, word_map))
    
    # isolate all kanji from the song
    kanji_list = extract_unicode_block(CONST_KANJI, lyrics)
    kanji_list = list(set(kanji_list))  # unique kanji only
    # build out a dictionary of kanji to readings and other information
    kanji_data_dict = get_all_kanji_data(kanji_list)
    
    translated_lines = translate_lyrics_lines(lyric_lines)
    
    return lyric_lines, word_map, kanji_data_dict, translated_lines

lyrics = """ねぇ どっかに置いてきたような事が
一つ二つ浮いているけど
ねぇ ちゃんと拾っておこう
はじけて忘れてしまう前に
回り出した あの子と僕の未来が止まり
どっかで またやり直せたら
回り出した あの子と僕が被害者面で
どっかを また練り歩けたらな
とぅるるる とぅるるる とぅるる
とぅるるる とぅるるる とぅるる
とぅるるる とぅるるる とぅるる
とぅるるる とぅるるる とぅるる
あのね 私あなたに会ったの
夢の中に置いてきたけどね
ねぇ どうして私が好きなの
一度しか会ったことがないのにね
思いを蹴って 二人でしてんだ
壊れない愛を歌う
言葉を二人に課して 誓いをたてんだ
忘れない愛を歌うようにね
回り出した あの子と僕の未来が止まり
どっかで またやり直せたら
回り出した あの子と僕が被害者面で
どっかを また練り歩けたらな
とぅるるる とぅるるる とぅるる
とぅるるる とぅるるる とぅるる
とぅるるる とぅるるる とぅるる
とぅるるる とぅるるる とぅるる
とぅるるる とぅるるる とぅるる
とぅるるる とぅるるる とぅるる
とぅるるる とぅるるる とぅるる
とぅるるる とぅるるる とぅるる
回り出した あの子と僕の未来が止まり
どっかで またやり直せたら
回り出した あの子と僕が被害者面で
どっかを また練り歩けたらな
時代に乗って僕たちは
変わらず愛に生きるだろう
僕らが散って残るのは
変わらぬ愛の歌なんだろうな
時代に乗って僕たちは
変わらず愛に生きるだろう
僕らが散って残るのは
変わらぬ愛の歌なんだろうな
とぅるるる とぅるるる とぅるる
とぅるるる とぅるるる とぅるる
とぅるるる とぅるるる とぅるる
とぅるるる とぅるるる とぅるる
"""

a, b, c, d = process_lyrics(lyrics)

print("Lyrics Lines:", a)
print("Word Map:", b)
print("Kanji Data:", c)

print(get_word_info("ばか"))

# #write to a file
# with open('output.json', 'w', encoding='utf-8') as f:
#     json.dump({
#         "lyrics_lines": a,
#         "word_map": b,
#         "kanji_data": c,
#         "translated_lines": d
#     }, f, ensure_ascii=False, indent=4)