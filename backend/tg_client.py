import asyncio
import logging
import os
from typing import AsyncGenerator, Optional
from telethon import TelegramClient, events
from telethon.tl.types import Document, MessageMediaDocument
from .config import TG_API_ID, TG_API_HASH, TG_BOT_TOKEN, TG_CHANNEL, SESSION_PATH
from .database import find_matching_anime, extract_episode_num, add_episode_from_tg, get_connection

logger = logging.getLogger("copperdub.tg")
logging.basicConfig(level=logging.INFO)

client: Optional[TelegramClient] = None
is_connected = False

def is_tg_configured() -> bool:
    return bool(TG_API_ID and TG_API_HASH and TG_BOT_TOKEN)

async def init_tg():
    global client, is_connected
    if not is_tg_configured():
        logger.warning("Telegram credentials not set. TG streaming and auto-sync disabled until .env is configured.")
        return

    try:
        client = TelegramClient(str(SESSION_PATH), TG_API_ID, TG_API_HASH)
        await client.start(bot_token=TG_BOT_TOKEN)
        is_connected = True
        register_handlers()
        me = await client.get_me()
        logger.info(f"Telethon client started as @{me.username}. Listening for new releases in @{TG_CHANNEL}...")
    except Exception as e:
        logger.error(f"Failed to start Telethon client: {e}")
        is_connected = False

def register_handlers():
    global client
    if not client:
        return

    @client.on(events.NewMessage(chats=TG_CHANNEL))
    async def handle_new_post(event):
        try:
            msg = event.message
            caption = msg.message or ""
            doc = getattr(msg, "document", None) or (msg.media.document if getattr(msg, "media", None) and hasattr(msg.media, "document") else None)
            mime = getattr(doc, "mime_type", "") if doc else ""
            is_video = "video" in mime

            logger.info(f"New incoming message {msg.id} in @{TG_CHANNEL}: has_video={is_video}, text={caption[:60]}")

            if not is_video and not caption:
                return

            anime_id = find_matching_anime(caption)
            if not anime_id:
                # Try auto-discovering new anime from Shikimori
                from .shikimori import search_shikimori, get_shikimori_details
                import re
                lines = [l.strip() for l in caption.split("\n") if l.strip()]
                if lines:
                    first_line = lines[0]
                    found = search_shikimori(first_line)
                    if found:
                        meta = get_shikimori_details(found["id"])
                        if meta:
                            conn = get_connection()
                            c = conn.cursor()
                            slug = re.sub(r'[^a-z0-9]+', '-', (meta['title_en'] or '').lower()).strip('-') or f"anime-{found['id']}"
                            c.execute("""
                            INSERT OR IGNORE INTO anime (slug, title_ru, title_en, format, episodes_done, episodes_total, status, poster_url, banner_url, description, aliases)
                            VALUES (?, ?, ?, ?, 0, ?, 'В процессе', ?, ?, ?, ?)
                            """, (
                                slug, meta['title_ru'], meta['title_en'], meta.get('kind', 'ТВ-сериал'),
                                meta['episodes_total'], meta['poster_url'], meta['banner_url'], meta['description'],
                                f"{meta['title_ru']}, {meta['title_en']}"
                            ))
                            conn.commit()
                            c.execute("SELECT id FROM anime WHERE slug = ?", (slug,))
                            row = c.fetchone()
                            if row:
                                anime_id = row['id']
                            conn.close()
                            logger.info(f"✨ Auto-created NEW anime '{meta['title_ru']}' with Shikimori cover & backdrop! (ID: {anime_id})")

            if not anime_id:
                logger.info(f"Post {msg.id} did not match known anime titles.")
                return

            ep_num_str, ep_order = extract_episode_num(caption)
            file_name = ""
            file_size = 0
            if doc:
                file_size = doc.size
                for attr in doc.attributes:
                    if hasattr(attr, "file_name"):
                        file_name = attr.file_name
                        break

            post_url = f"https://t.me/{TG_CHANNEL}/{msg.id}"
            
            # Check existing
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
            SELECT id FROM episodes 
            WHERE anime_id = ? AND (episode_order = ? OR episode_num LIKE ?)
            """, (anime_id, ep_order, f"%{int(ep_order) if ep_order.is_integer() else ep_order}%"))
            existing = c.fetchone()
            
            if existing:
                c.execute("""
                UPDATE episodes 
                SET tg_message_id = ?, tg_post_url = ?, file_name = ?, file_size = ?
                WHERE id = ?
                """, (msg.id, post_url, file_name, file_size, existing['id']))
                conn.commit()
            else:
                add_episode_from_tg(
                    anime_id=anime_id,
                    ep_num_str=ep_num_str,
                    ep_order=ep_order,
                    caption=caption,
                    tg_message_id=msg.id,
                    tg_post_url=post_url,
                    file_name=file_name,
                    file_size=file_size
                )
            conn.close()
            logger.info(f"Auto-added / updated post #{msg.id} for Anime ID {anime_id}")
        except Exception as e:
            logger.error(f"Error handling new post in Telegram channel: {e}", exc_info=True)

async def sync_channel(limit: int = 120) -> dict:
    """
    Scans posts by ID in batches (compatible with Telegram Bot API restrictions).
    """
    global client, is_connected
    if not is_connected or not client:
        return {"status": "error", "message": "Telegram-клиент не подключен. Проверьте .env"}

    added_or_updated = 0
    scanned = 0

    try:
        chat = await client.get_entity(TG_CHANNEL)
        batch_size = 20
        for start_id in range(1, limit + 1, batch_size):
            ids = list(range(start_id, start_id + batch_size))
            msgs = await client.get_messages(chat, ids=ids)
            for m in msgs:
                if not m:
                    continue
                scanned += 1
                caption = m.message or ""
                doc = getattr(m, "document", None) or (m.media.document if getattr(m, "media", None) and hasattr(m.media, "document") else None)
                mime = getattr(doc, "mime_type", "") if doc else ""
                is_video = "video" in mime

                if not is_video and not caption:
                    continue

                anime_id = find_matching_anime(caption)
                if not anime_id:
                    continue

                ep_num_str, ep_order = extract_episode_num(caption)
                file_name = ""
                file_size = 0
                if doc:
                    file_size = doc.size
                    for attr in doc.attributes:
                        if hasattr(attr, "file_name"):
                            file_name = attr.file_name
                            break

                post_url = f"https://t.me/{TG_CHANNEL}/{m.id}"
                conn = get_connection()
                c = conn.cursor()
                c.execute("""
                SELECT id FROM episodes 
                WHERE anime_id = ? AND (episode_order = ? OR episode_num LIKE ?)
                """, (anime_id, ep_order, f"%{int(ep_order) if ep_order.is_integer() else ep_order}%"))
                existing = c.fetchone()
                
                if existing:
                    c.execute("""
                    UPDATE episodes 
                    SET tg_message_id = ?, tg_post_url = ?, file_name = ?, file_size = ?
                    WHERE id = ?
                    """, (m.id, post_url, file_name, file_size, existing['id']))
                    conn.commit()
                else:
                    add_episode_from_tg(
                        anime_id=anime_id,
                        ep_num_str=ep_num_str,
                        ep_order=ep_order,
                        caption=caption,
                        tg_message_id=m.id,
                        tg_post_url=post_url,
                        file_name=file_name,
                        file_size=file_size
                    )
                conn.close()
                added_or_updated += 1

        return {
            "status": "ok",
            "scanned": scanned,
            "added_or_updated": added_or_updated,
            "channel": TG_CHANNEL
        }
    except Exception as e:
        logger.error(f"Error in sync_channel: {e}")
        return {"status": "error", "message": str(e)}

async def get_tg_message_document(message_id: int):
    """
    Returns (document, file_size, mime_type) for a given message in the channel.
    """
    global client, is_connected
    if not is_connected or not client:
        return None, 0, "video/mp4"

    try:
        chat = await client.get_entity(TG_CHANNEL)
        msg = await client.get_messages(chat, ids=message_id)
        if not msg:
            return None, 0, "video/mp4"

        doc = getattr(msg, "document", None) or (msg.media.document if getattr(msg, "media", None) and hasattr(msg.media, "document") else None)
        if not doc:
            return None, 0, "video/mp4"

        return doc, doc.size, getattr(doc, "mime_type", "video/mp4")
    except Exception as e:
        logger.error(f"Failed to fetch document for message {message_id}: {e}")
        return None, 0, "video/mp4"

async def stream_tg_media_chunks(document: Document, start: int, end: int, chunk_size: int = 128 * 1024) -> AsyncGenerator[bytes, None]:
    """
    Streams byte range [start, end] from Telegram MTProto document in chunks.
    Automatically aligns offsets to 4096-byte boundaries as required by MTProto,
    and slices the exact requested bytes for smooth HTML5 video player seeking.
    """
    global client
    if not client:
        return

    requested_len = end - start + 1
    
    # Telegram MTProto requires offsets to be multiples of 4096 (or 1KB)
    align = 4096
    aligned_start = (start // align) * align
    skip_prefix = start - aligned_start
    total_to_read = requested_len + skip_prefix
    
    bytes_streamed = 0
    buffer = bytearray()
    
    async for chunk in client.iter_download(
        document,
        offset=aligned_start,
        limit=total_to_read,
        chunk_size=chunk_size,
        request_size=chunk_size
    ):
        if skip_prefix > 0:
            if len(chunk) <= skip_prefix:
                skip_prefix -= len(chunk)
                continue
            else:
                chunk = chunk[skip_prefix:]
                skip_prefix = 0
                
        # Limit to remaining requested bytes
        remaining = requested_len - bytes_streamed
        if len(chunk) > remaining:
            chunk = chunk[:remaining]
            
        bytes_streamed += len(chunk)
        yield chunk
        
        if bytes_streamed >= requested_len:
            break
