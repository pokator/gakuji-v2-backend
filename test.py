import requests
import json

# Test the API locally
BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print("Health Check:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    print("\n" + "="*50 + "\n")

def test_process_lyrics():
    """Test processing Japanese lyrics"""
    test_lyrics = """朝目が覚めたら
置いてきぼりになった
みたいだこんな気持ち"""
    
    payload = {
        "lyrics": test_lyrics
    }
    
    response = requests.post(f"{BASE_URL}/process-lyrics", json=payload)
    
    if response.status_code == 200:
        result = response.json()
        print("Lyrics Processing Result:")
        print(f"Number of lines: {len(result['lyrics_lines'])}")
        print(f"Unique words: {len(result['word_map'])}")
        print(f"Unique kanji: {len(result['kanji_data'])}")
        print("\nTranslated lines:")
        for original, translation in result['translated_lines'][:3]:
            print(f"  {original} → {translation}")
    else:
        print(f"Error: {response.status_code}")
        print(response.json())

if __name__ == "__main__":
    print("Testing Japanese Lyrics Processor API\n")
    
    try:
        test_health()
        test_process_lyrics()
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the server.")
        print("Make sure the server is running with: python main.py")
    except Exception as e:
        print(f"ERROR: {e}")