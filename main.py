import os

from dotenv import load_dotenv

load_dotenv()

from app.main import app

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "localhost")
    uvicorn.run(app, host=host, port=port)