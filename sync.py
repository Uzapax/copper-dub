import asyncio
import os
import json
import re
import urllib.parse
import urllib.request
import ssl
from telethon import TelegramClient

TG_API_ID = int(os.environ.get("TG_API_ID", "0"))
TG_API_HASH = os.environ.get("TG_API_HASH", "")
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
TG_CHANNEL = os.environ.get("TG_CHANNEL", "gygdub")

SHIKIMORI_API = "https://shikimori.one/api"
USER_AGENT = "CopperDub/1.0 (Anime Voiceover Studio)"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def search_shikimori(title):
    clean = title
    for token in ["(1 сезон)", "(2 сезон)", "(Куры 1–3)", "ТВ-сериал", "Сезон 1"]:
        clean = clean.replace(token, "")
    url = f"{SHIKIMORI_API}/animes?search={urllib.parse.quote(clean.strip())}&limit=1"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
            res = json.loads(r.read().decode("utf-8"))
            if res:
                found = res[0]
                # Details
                d_req = urllib.request.Request(f"{SHIKIMORI_API}/animes/{found['id']}", headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(d_req, timeout=8, context=ctx) as dr:
                    d = json.loads(dr.read().decode("utf-8"))
                    img = d.get("image", {})
                    p = img.get("original") or img.get("preview")
                    poster_url = f"https://shikimori.one{p}" if p and p.startswith("/") else (p or "")
                    return {
                        "title_ru": d.get("russian") or d.get("name"),
                        "title_en": d.get("name") or "",
                        "poster_url": poster_url,
                        "description": d.get("description") or "",
                        "episodes_total": d.get("episodes") or 0,
                        "kind": d.get("kind") or "tv"
                    }
    except Exception as e:
        print(f"Shikimori lookup error: {e}")
    return None

def extract_episode_num(text):
    if not text:
        return "1 серия", 1.0
    text_lower = text.lower()
    if "фильм" in text_lower:
        return "Фильм", 1.0
    if "спешл" in text_lower:
        return "Спешл", 1.0
    m = re.search(r'(\d+)\s*(?:серия|эп|эпизод)', text_lower)
    if m:
        n = int(m.group(1))
        return f"{n} серия", float(n)
    m2 = re.search(r'сери[яи]\s*(\d+)', text_lower)
    if m2:
        n = int(m2.group(1))
        return f"{n} серия", float(n)
    return text.strip()[:30], 1.0

async def sync():
    catalog_path = "catalog.json"
    if not os.path.exists(catalog_path):
        catalog_path = "frontend/catalog.json"
        
    with open(catalog_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)
        
    print(f"Loaded {len(catalog)} anime from {catalog_path}")
    
    client = TelegramClient("github_sync_session", TG_API_ID, TG_API_HASH)
    await client.start(bot_token=TG_BOT_TOKEN)
    chat = await client.get_entity(TG_CHANNEL)
    
    changes = False
    added_count = 0
    
    # Check last 40 posts by ID
    # Get highest message ID by checking first
    test_ids = list(range(60, 110))
    msgs = await client.get_messages(chat, ids=test_ids)
    
    for m in msgs:
        if not m:
            continue
        caption = m.message or ""
        doc = getattr(m, "document", None) or (m.media.document if getattr(m, "media", None) and hasattr(m.media, "document") else None)
        mime = getattr(doc, "mime_type", "") if doc else ""
        if "video" not in mime and not caption:
            continue
            
        # Match anime in catalog
        matched_anime = None
        for a in catalog:
            keys = [a["title_ru"].lower()]
            if a.get("title_en"):
                keys.append(a["title_en"].lower())
            if a.get("aliases"):
                keys.extend([x.strip().lower() for x in a["aliases"].split(",") if x.strip()])
                
            for k in keys:
                if len(k) >= 3 and k in caption.lower():
                    matched_anime = a
                    break
            if matched_anime:
                break
                
        # If not matched, try discovering new anime via Shikimori
        if not matched_anime:
            first_line = caption.split("\n")[0].strip()
            shiki_data = search_shikimori(first_line)
            if shiki_data:
                new_id = max([a.get("id", 0) for a in catalog] + [0]) + 1
                matched_anime = {
                    "id": new_id,
                    "slug": re.sub(r'[^a-z0-9]+', '-', (shiki_data['title_en'] or first_line).lower()).strip('-'),
                    "title_ru": shiki_data["title_ru"],
                    "title_en": shiki_data["title_en"],
                    "format": shiki_data.get("kind", "ТВ-сериал"),
                    "episodes_done": 0,
                    "episodes_total": shiki_data["episodes_total"],
                    "status": "В процессе",
                    "cast": "Copper Dub",
                    "poster_url": shiki_data["poster_url"],
                    "banner_url": shiki_data["poster_url"],
                    "description": shiki_data["description"],
                    "aliases": f"{shiki_data['title_ru']}, {shiki_data['title_en']}",
                    "episodes": []
                }
                catalog.append(matched_anime)
                changes = True
                print(f"✨ Auto-created NEW anime from Shikimori: {matched_anime['title_ru']}")
                
        if not matched_anime:
            continue
            
        ep_num_str, ep_order = extract_episode_num(caption)
        file_size = doc.size if doc else 0
        post_url = f"https://t.me/{TG_CHANNEL}/{m.id}"
        
        # Check if episode is already registered
        episodes = matched_anime.get("episodes", [])
        existing = next((e for e in episodes if e.get("tg_message_id") == m.id or e.get("episode_num") == ep_num_str), None)
        
        if existing:
            if not existing.get("tg_message_id"):
                existing["tg_message_id"] = m.id
                existing["tg_post_url"] = post_url
                existing["file_size"] = file_size
                changes = True
                added_count += 1
                print(f"✓ Linked existing episode '{existing['episode_num']}' to TG #{m.id}")
        else:
            new_ep = {
                "id": max([e.get("id", 0) for a in catalog for e in a.get("episodes", [])] + [0]) + 1,
                "anime_id": matched_anime["id"],
                "episode_num": ep_num_str,
                "episode_order": ep_order,
                "title": ep_num_str,
                "cast_credits": "Copper Dub",
                "sub_credits": "",
                "notes": caption[:150],
                "tg_message_id": m.id,
                "tg_post_url": post_url,
                "file_size": file_size
            }
            episodes.append(new_ep)
            episodes.sort(key=lambda x: x.get("episode_order", 0))
            matched_anime["episodes"] = episodes
            matched_anime["episodes_done"] = len(episodes)
            changes = True
            added_count += 1
            print(f"+ ADDED episode '{ep_num_str}' (TG #{m.id}) to {matched_anime['title_ru']}")
            
    await client.disconnect()
    
    if changes:
        with open(catalog_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        print(f"SUCCESS: Catalog updated with {added_count} new/linked episodes!")
        print("CHANGES_DETECTED=1")
    else:
        print("Catalog is already up to date. No new episodes found.")
        print("CHANGES_DETECTED=0")

if __name__ == "__main__":
    asyncio.run(sync())
