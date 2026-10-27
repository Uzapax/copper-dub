import os
import json
from pathlib import Path
from .config import BASE_DIR
from .database import get_connection

def export_static_catalog():
    """
    Exports all anime and episodes to frontend/catalog.json.
    This allows frontend to be deployed to Cloudflare Pages as a pure 100% free static site!
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM anime ORDER BY status = 'В процессе' DESC, updated_at DESC")
    animes = [dict(r) for r in c.fetchall()]
    
    for a in animes:
        c.execute("SELECT * FROM episodes WHERE anime_id = ? ORDER BY episode_order ASC, id ASC", (a["id"],))
        a["episodes"] = [dict(r) for r in c.fetchall()]
        
    conn.close()
    
    out_file = BASE_DIR / "frontend" / "catalog.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(animes, f, ensure_ascii=False, indent=2)
        
    print(f"Exported static catalog with {len(animes)} anime to {out_file}")
    return len(animes)

if __name__ == "__main__":
    export_static_catalog()
