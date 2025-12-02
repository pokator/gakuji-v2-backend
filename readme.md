# Japanese Lyrics Processor API

A FastAPI-based backend service that processes Japanese song lyrics, providing tokenization, word definitions, kanji information, and English translations.

## Features

- 📝 **Tokenization**: Breaks down Japanese lyrics into meaningful word segments
- 📚 **Dictionary Lookups**: Provides definitions and readings for Japanese words
- 🔤 **Kanji Analysis**: Detailed information about kanji characters including JLPT levels, meanings, and readings
- 🌐 **Translation**: Automatic English translation via DeepL API
- 🔧 **Dakuten/Handakuten Correction**: Fixes common character encoding issues in Japanese text
- ⚡ **Fast API**: RESTful API with automatic documentation

## Prerequisites

- Python 3.8 or higher
- DeepL API key (free tier available at [deepl.com](https://www.deepl.com/pro-api))
- Git (for cloning the repository)

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd gakuji-rewrite
```

### 2. Create a Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** The `jamdict` library will use a shared database location at `~/.jamdict/` by default. The first time you run the application, it may need to download dictionary data.

### 4. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your DeepL API key:

```env
DEEPL_KEY=your_deepl_api_key_here
PORT=8000
```

**Important:** Never commit your `.env` file to version control!

### 5. Ensure Required Files Exist

Make sure these files are in your project directory:
- `kanji.json` - Kanji database (should be included in the repo)
- `main.py` - Main application file

## Running Locally

### Start the Server

```bash
python main.py
```

The server will start at `http://localhost:8000`

### Test the API

**Option 1: Interactive Documentation**
- Open your browser to `http://localhost:8000/docs`
- Try the `/process-lyrics` endpoint with sample Japanese lyrics

**Option 2: Test Script**
```bash
python test_client.py
```

**Option 3: cURL**
```bash
curl -X POST "http://localhost:8000/process-lyrics" \
  -H "Content-Type: application/json" \
  -d '{"lyrics": "朝目が覚めたら\n置いてきぼりになった"}'
```

## API Endpoints

### `GET /`
Welcome endpoint with API information.

**Response:**
```json
{
  "message": "Japanese Lyrics Processor API",
  "endpoints": {
    "/process-lyrics": "POST - Process Japanese lyrics",
    "/health": "GET - Health check",
    "/docs": "GET - Interactive API documentation"
  }
}
```

### `GET /health`
Health check endpoint to verify the service is running.

**Response:**
```json
{
  "status": "healthy",
  "deepl_api": "connected",
  "jamdict": "loaded",
  "kanji_data": "2136 kanji loaded"
}
```

**Request Body:**
```json
{
  "lyrics": "朝目が覚めたら\n置いてきぼりになった"
}
```

**Response:**
```json
{
  "lyrics_lines": [
    ["朝", "目", "が", "覚め", "たら"],
    ["置い", "て", "きぼり", "に", "なっ", "た"]
  ],
  "word_map": {
    "朝": [
      {
        "idseq": "1234567",
        "word": "朝",
        "furigana": "あさ",
        "definitions": [
          {
            "pos": ["noun"],
            "definition": ["morning"]
          }
        ]
      }
    ]
  },
  "kanji_data": {
    "朝": {
      "jlpt_new": 5,
      "meanings": ["morning", "dynasty", "regime", "epoch", "period"],
      "readings_on": ["チョウ"],
      "readings_kun": ["あさ"],
      "radicals": ["月", "十", "日"]
    }
  },
  "translated_lines": [
    ["朝目が覚めたら", "When I woke up in the morning"],
    ["置いてきぼりになった", "I was left behind"]
  ]
}
```

## Project Structure

```
gakuji-rewrite/
├── main.py              # FastAPI application
├── kanji.json           # Kanji database
├── test_client.py       # Test script
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not in git)
├── .env.example         # Environment template
├── .gitignore          # Git ignore file
└── README.md           # This file
```

## Deployment to Render


### Step 1: Prepare for Deployment

1. **Copy Jamdict Database to Project** (if using local database):
   ```bash
   mkdir jamdict_data
   # Windows
   copy %USERPROFILE%\.jamdict\data\jamdict.db jamdict_data\
   # Mac/Linux
   cp ~/.jamdict/data/jamdict.db jamdict_data/
   ```

2. **Update .gitignore** (if not using local database):
   ```
   .env
   __pycache__/
   *.pyc
   output.json
   jamdict_data/
   ```

3. **Commit and Push to GitHub**:
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

### Step 2: Deploy on Render

1. **Create New Web Service**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**
   - **Name**: `japanese-lyrics-api` (or your choice)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`

3. **Set Environment Variables**
   - Click "Advanced" → "Add Environment Variable"
   - Add: `DEEPL_KEY` = `your_deepl_api_key`
   - (Optional) Add: `JAMDICT_DB_PATH` = `/opt/render/project/src/jamdict_data/jamdict.db`

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment to complete (~5-10 minutes first time)

### Step 3: Test Deployment

Your API will be available at: `https://your-service-name.onrender.com`

Test with:
```bash
curl https://your-service-name.onrender.com/health
```

### Important Notes for Render

- **Cold Starts**: Free tier services sleep after 15 minutes of inactivity. First request after sleep takes ~30-60 seconds.
- **Build Time**: Initial builds can take 5-10 minutes due to dependency installation.
- **Memory Limits**: Free tier has 512MB RAM. Monitor usage if processing large lyrics.
- **Monthly Limits**: 750 hours/month (enough for 24/7 uptime of one service).

## Development

### Adding New Dependencies

```bash
# Activate virtual environment
venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate    # Mac/Linux

# Install new package
pip install package-name

# Update requirements.txt
pip freeze | Out-File -Encoding utf8 requirements.txt  # Windows PowerShell
pip freeze > requirements.txt                          # Mac/Linux/cmd
```

### Running Tests

```bash
python test_client.py
```

### Debugging

Enable debug mode by setting environment variable:
```bash
export DEBUG=true  # Mac/Linux
$env:DEBUG="true"  # PowerShell
```

View logs:
```bash
# Local
# Logs appear in your terminal

# Render
# View logs in the Render dashboard under "Logs" tab
```

## Troubleshooting

### Issue: `jamdict-data` won't install on Windows

**Solution:** You don't need it! Use the default Jamdict database location:
```bash
pip install jamdict  # Skip jamdict-data
```

### Issue: DeepL API rate limits

**Solution:** 
- Free tier: 500,000 characters/month
- Implement caching to reduce API calls
- Consider upgrading to DeepL Pro

### Issue: Memory errors on Render

**Solution:**
- Upgrade to paid tier for more RAM
- Optimize `memory_mode` setting in Jamdict initialization
- Process lyrics in smaller chunks

### Issue: Cold start timeouts

**Solution:**
- Upgrade to paid tier ($7/month) for always-on service
- Accept 30-60 second initial delay on free tier
- Consider a keep-alive service (ping every 14 minutes)

### Issue: Port already in use

**Solution:**
```bash
# Kill process using port 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Mac/Linux
lsof -ti:8000 | xargs kill
```

## API Rate Limits

- **DeepL Free**: 500,000 characters/month
- **DeepL Pro**: Starts at 100,000 characters for $5.49/month
- **Render Free**: 750 compute hours/month, 100GB bandwidth

## Security Notes

- Never commit `.env` files
- Rotate API keys regularly
- Use environment variables for all sensitive data
- Enable CORS restrictions for production (update `allow_origins` in `main.py`)

## Performance Optimization

### For Production:

1. **Enable Caching**
   - Cache translated lines
   - Cache word lookups
   - Use Redis or in-memory cache

2. **Database Optimization**
   - Use `memory_mode=True` for Jamdict (already enabled)
   - Consider preloading frequently used data

3. **Async Processing**
   - Already using FastAPI's async capabilities
   - Consider background tasks for long-running operations

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

## Support

For issues and questions:
- GitHub Issues: [Your repo URL]/issues
- Email: [Your email]

## Acknowledgments

- [Janome](https://mocobeta.github.io/janome/en/) - Japanese morphological analyzer
- [Jamdict](https://github.com/neocl/jamdict) - Japanese dictionary interface
- [DeepL](https://www.deepl.com/) - Translation API
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework

## Version History

### v1.0.0 (Current)
- Initial release
- Japanese lyrics processing
- Word tokenization and definitions
- Kanji analysis
- English translation
- RESTful API with FastAPI