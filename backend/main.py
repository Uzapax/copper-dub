import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Response, HTTPException, status, Header
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import BASE_DIR, TG_CHANNEL, TG_API_ID, TG_BOT_TOKEN
from .database import (
    init_db, get_all_anime, get_anime_by_id, get_episode_by_id,
    get_connection, update_episode_tg_id
)
from .tg_client import (
    init_tg, is_connected, is_tg_configured,
    get_tg_message_document, stream_tg_media_chunks, sync_channel
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database and Telegram client
    init_db()
    await init_tg()
    yield
    # Shutdown logic if any

app = FastAPI(title="Copper Dub API", lifespan=lifespan)

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = BASE_DIR / "frontend"

# --- API Endpoints ---

@app.get("/api/status")
async def get_system_status():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as count FROM anime")
    anime_cnt = c.fetchone()["count"]
    c.execute("SELECT COUNT(*) as count FROM episodes")
    ep_cnt = c.fetchone()["count"]
    c.execute("SELECT COUNT(*) as count FROM episodes WHERE tg_message_id IS NOT NULL")
    linked_ep_cnt = c.fetchone()["count"]
    conn.close()

    return {
        "tg_configured": is_tg_configured(),
        "tg_connected": is_connected,
        "tg_channel": TG_CHANNEL,
        "anime_count": anime_cnt,
        "episodes_count": ep_cnt,
        "episodes_linked_to_tg": linked_ep_cnt
    }

class ConfigPayload(BaseModel):
    api_id: str
    api_hash: str
    bot_token: str = ""
    channel: str = "gygdub"

@app.post("/api/config")
async def update_config(payload: ConfigPayload):
    env_file = BASE_DIR / ".env"
    with open(env_file, "w", encoding="utf-8") as f:
        f.write(f"TG_API_ID={payload.api_id.strip()}\n")
        f.write(f"TG_API_HASH={payload.api_hash.strip()}\n")
        f.write(f"TG_BOT_TOKEN={payload.bot_token.strip()}\n")
        f.write(f"TG_CHANNEL={payload.channel.strip()}\n")
        f.write("PORT=8000\n")

    return {
        "status": "ok",
        "message": "Настройки сохранены! Перезапустите сервер, чтобы подключиться к Telegram."
    }

@app.get("/api/anime")
async def list_anime(status: str = None, search: str = None):
    return get_all_anime(status_filter=status, search=search)

@app.get("/api/anime/{anime_id}")
async def get_anime_details(anime_id: int):
    item = get_anime_by_id(anime_id)
    if not item:
        raise HTTPException(status_code=404, detail="Anime not found")
    return item

@app.post("/api/sync")
async def trigger_sync(limit: int = 100):
    res = await sync_channel(limit=limit)
    return res

from .shikimori import update_anime_from_shikimori, sync_all_anime_shikimori

@app.post("/api/anime/{anime_id}/sync-shikimori")
async def sync_anime_shikimori(anime_id: int):
    meta = update_anime_from_shikimori(anime_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Аниме не найдено на Shikimori")
    return {"status": "ok", "metadata": meta}

@app.post("/api/shikimori/sync-all")
async def sync_all_shikimori():
    cnt = sync_all_anime_shikimori()
    return {"status": "ok", "updated_anime_count": cnt}

class LinkEpisodePayload(BaseModel):
    episode_id: int
    tg_message_id: int

@app.post("/api/link-episode")
async def link_episode(payload: LinkEpisodePayload):
    url = f"https://t.me/{TG_CHANNEL}/{payload.tg_message_id}"
    update_episode_tg_id(payload.episode_id, payload.tg_message_id, url)
    return {"status": "ok", "url": url}

@app.get("/api/stream/{message_id}")
async def stream_video(message_id: int, request: Request, range: str = Header(None)):
    """
    HTTP 206 Partial Content video streaming directly from Telegram.
    Accepts standard browser Range headers (e.g. 'Range: bytes=0-1000000').
    """
    doc, file_size, mime_type = await get_tg_message_document(message_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Video post #{message_id} not found in @{TG_CHANNEL} or Telegram is not connected"
        )

    start = 0
    end = file_size - 1

    if range:
        try:
            range_val = range.replace("bytes=", "").split("-")
            start = int(range_val[0]) if range_val[0] else 0
            end = int(range_val[1]) if len(range_val) > 1 and range_val[1] else file_size - 1
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                detail="Invalid Range header"
            )

    if start > end or start >= file_size:
        raise HTTPException(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            detail="Requested range out of bounds"
        )

    # Limit chunk length per request to prevent overload
    chunk_length = end - start + 1
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_length),
        "Content-Type": mime_type,
        "Cache-Control": "public, max-age=3600"
    }

    return StreamingResponse(
        stream_tg_media_chunks(doc, start, end),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers
    )

# --- Serve Frontend ---
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
