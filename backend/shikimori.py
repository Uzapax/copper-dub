import json
import logging
import urllib.parse
import urllib.request
import ssl
from typing import Optional, Dict, Any
from .database import get_connection

logger = logging.getLogger("copperdub.shikimori")

# Shikimori API base
SHIKIMORI_API = "https://shikimori.one/api"
USER_AGENT = "CopperDub/1.0 (Anime Voiceover Studio; contact: gygdub)"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def clean_search_title(title: str) -> str:
    """
    Cleans up titles for search, removing season suffixes like '(1 сезон)'.
    """
    cleaned = title
    for token in ["(1 сезон)", "(2 сезон)", "(3 сезон)", "(Куры 1–3)", "ТВ-сериал", "Сезон 1"]:
        cleaned = cleaned.replace(token, "")
    return cleaned.strip()

def search_shikimori(title: str) -> Optional[Dict[str, Any]]:
    """
    Searches Shikimori API for an anime title.
    """
    clean_title = clean_search_title(title)
    url = f"{SHIKIMORI_API}/animes?search={urllib.parse.quote(clean_title)}&limit=1"
    
    headers = {"User-Agent": USER_AGENT}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
            results = json.loads(resp.read().decode("utf-8"))
            if results and len(results) > 0:
                return results[0]
    except Exception as e:
        logger.error(f"Shikimori search error for '{clean_title}': {e}")
    return None

def get_shikimori_details(anime_id: int) -> Optional[Dict[str, Any]]:
    """
    Gets detailed anime info and screenshots from Shikimori.
    """
    headers = {"User-Agent": USER_AGENT}
    
    # 1. Anime details
    url = f"{SHIKIMORI_API}/animes/{anime_id}"
    details = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
            details = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to fetch Shikimori anime details for ID {anime_id}: {e}")
        return None

    # 2. Screenshots (for backdrop banner)
    screenshots_url = f"{SHIKIMORI_API}/animes/{anime_id}/screenshots"
    banner_url = ""
    try:
        req_shots = urllib.request.Request(screenshots_url, headers=headers)
        with urllib.request.urlopen(req_shots, timeout=8, context=ctx) as resp:
            shots = json.loads(resp.read().decode("utf-8"))
            if shots and len(shots) > 0:
                orig = shots[0].get("original")
                if orig:
                    banner_url = f"https://shikimori.one{orig}" if orig.startswith("/") else orig
    except Exception as e:
        logger.warning(f"Failed to fetch screenshots for ID {anime_id}: {e}")

    # Build standardized metadata
    img = details.get("image", {})
    poster_path = img.get("original") or img.get("preview")
    poster_url = f"https://shikimori.one{poster_path}" if poster_path and poster_path.startswith("/") else (poster_path or "")

    return {
        "shikimori_id": anime_id,
        "title_ru": details.get("russian") or details.get("name"),
        "title_en": details.get("name") or details.get("english", [""])[0] if isinstance(details.get("english"), list) else details.get("name"),
        "poster_url": poster_url,
        "banner_url": banner_url or poster_url,
        "description": details.get("description") or "",
        "episodes_total": details.get("episodes") or 0,
        "status": "Завершено" if details.get("status") == "released" else "В процессе",
        "kind": details.get("kind") or "tv"
    }

def update_anime_from_shikimori(db_anime_id: int, query: str = None) -> Optional[Dict[str, Any]]:
    """
    Fetches latest metadata from Shikimori and updates database.
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, title_ru, title_en, poster_url, banner_url, description FROM anime WHERE id = ?", (db_anime_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None

    search_query = query or row["title_ru"] or row["title_en"]
    found = search_shikimori(search_query)
    if not found:
        # Fallback to English title if available
        if row["title_en"]:
            found = search_shikimori(row["title_en"])
    
    if not found:
        conn.close()
        logger.info(f"Anime '{search_query}' not found on Shikimori.")
        return None

    meta = get_shikimori_details(found["id"])
    if not meta:
        conn.close()
        return None

    # Update database
    c.execute("""
    UPDATE anime 
    SET poster_url = COALESCE(NULLIF(?, ''), poster_url),
        banner_url = COALESCE(NULLIF(?, ''), banner_url),
        description = CASE WHEN (description IS NULL OR description = '' OR description = 'Описание отсутствует.') THEN ? ELSE description END,
        title_en = COALESCE(NULLIF(?, ''), title_en),
        episodes_total = CASE WHEN (episodes_total = 0 AND ? > 0) THEN ? ELSE episodes_total END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (
        meta["poster_url"],
        meta["banner_url"],
        meta["description"],
        meta["title_en"],
        meta["episodes_total"],
        meta["episodes_total"],
        db_anime_id
    ))
    conn.commit()
    conn.close()
    
    logger.info(f"Updated Anime #{db_anime_id} from Shikimori: Poster={meta['poster_url']}")
    return meta

def sync_all_anime_shikimori():
    """
    Enriches all anime in the database with Shikimori posters and banners.
    """
    import time
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, title_ru FROM anime")
    rows = c.fetchall()
    conn.close()

    updated_count = 0
    for r in rows:
        res = update_anime_from_shikimori(r["id"])
        if res:
            updated_count += 1
        time.sleep(0.3)
    return updated_count
