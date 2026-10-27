import asyncio
import os
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, r'C:\Users\glebu\copper-dub')
from telethon import TelegramClient
from backend.database import get_connection, find_matching_anime, extract_episode_num, add_episode_from_tg
from backend.config import TG_API_ID, TG_API_HASH, TG_BOT_TOKEN, TG_CHANNEL, SESSION_PATH

async def auto_sync_all_existing_posts():
    print(f"Starting initial sync with @{TG_CHANNEL}...")
    client = TelegramClient(str(SESSION_PATH), TG_API_ID, TG_API_HASH)
    await client.start(bot_token=TG_BOT_TOKEN)
    chat = await client.get_entity(TG_CHANNEL)
    
    total_matched = 0
    # Scan posts in batches from 1 to 120
    batch_size = 20
    for start_id in range(1, 120, batch_size):
        ids = list(range(start_id, start_id + batch_size))
        try:
            msgs = await client.get_messages(chat, ids=ids)
            for m in msgs:
                if not m:
                    continue
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
                
                # Check if this episode is in database
                conn = get_connection()
                c = conn.cursor()
                
                # Try to find episode by order or num string
                c.execute("""
                SELECT id, episode_num FROM episodes 
                WHERE anime_id = ? AND (episode_order = ? OR episode_num LIKE ?)
                """, (anime_id, ep_order, f"%{int(ep_order) if ep_order.is_integer() else ep_order}%"))
                existing = c.fetchone()
                
                if existing:
                    ep_id = existing['id']
                    c.execute("""
                    UPDATE episodes 
                    SET tg_message_id = ?, tg_post_url = ?, file_name = ?, file_size = ?
                    WHERE id = ?
                    """, (m.id, post_url, file_name, file_size, ep_id))
                    conn.commit()
                    print(f"✓ Linked Post #{m.id} -> Anime ID {anime_id} Ep '{existing['episode_num']}' ({file_size / (1024*1024):.1f} MB)")
                    total_matched += 1
                else:
                    # New episode not in original excel!
                    ep_id = add_episode_from_tg(
                        anime_id=anime_id,
                        ep_num_str=ep_num_str,
                        ep_order=ep_order,
                        caption=caption,
                        tg_message_id=m.id,
                        tg_post_url=post_url,
                        file_name=file_name,
                        file_size=file_size
                    )
                    print(f"+ ADDED NEW EPISODE #{ep_num_str} from Post #{m.id} -> Anime ID {anime_id} ({file_size / (1024*1024):.1f} MB)")
                    total_matched += 1
                conn.close()
        except Exception as e:
            print(f"Error checking batch {start_id}..{start_id+batch_size}: {e}")

    await client.disconnect()
    print(f"\nFinished sync! Total episodes linked or added: {total_matched}")

if __name__ == "__main__":
    asyncio.run(auto_sync_all_existing_posts())
