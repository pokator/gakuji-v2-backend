from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.routers.lyrics import router
from app.exceptions import LyricsProcessingError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Japanese Lyrics Processor API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)


# Health check endpoint for readiness/liveness probes
@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}

# Exception handlers
@app.exception_handler(LyricsProcessingError)
async def lyrics_processing_exception_handler(request: Request, exc: LyricsProcessingError):
    logger.error(f"Lyrics processing error: {exc}")
    raise HTTPException(status_code=500, detail="Lyrics processing failed")