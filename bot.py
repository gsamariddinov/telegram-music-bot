"""
Tunova — Telegram Music Bot  @Tunova\_Bot
Features: search, download MP3, history, favorites, top, language, inline, voice recognition
"""
import os
import uuid
import asyncio
import logging
import tempfile
import urllib.request

from dotenv import load_dotenv
import yt_dlp
from aiohttp import web

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction

import db
import i18n
import music_api

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN    = os.getenv("BOT_TOKEN", "8718633686:AAHYLrAu-m16E2Umpz-o3P1O2Xy3eT2AiAY")
BOT_NAME     = "Tunova"
BOT_USERNAME = "Tunova_Bot"
MAX_RESULTS  = 5
MAX_DURATION = 600   # seconds


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

def fmt_duration(seconds) -> str:
    if not seconds:
        return "??:??"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def get_main_menu(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(i18n.t(lang, "menu_history")),
                KeyboardButton(i18n.t(lang, "menu_favorites")),
            ],
            [
                KeyboardButton(i18n.t(lang, "menu_top")),
                KeyboardButton(i18n.t(lang, "menu_lang")),
                KeyboardButton(i18n.t(lang, "menu_help")),
            ]
        ],
        resize_keyboard=True
    )


def _has_ffmpeg() -> bool:
    import shutil
    return shutil.which("ffmpeg") is not None


def search_music(query: str, max_results: int = MAX_RESULTS) -> list:
    """Primary music search using direct MP3 catalog with YouTube fallback."""
    tracks = music_api.search_music(query, max_results)
    if tracks:
        return tracks
    try:
        return search_youtube(query, max_results)
    except Exception as e:
        logger.warning(f"YouTube fallback search failed: {e}")
        return []


def search_youtube(query: str, max_results: int = MAX_RESULTS) -> list:
    """Fallback search on YouTube."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "default_search": "ytsearch",
        "noplaylist": True,
        "extractor_args": {"youtube": ["player_client=android"]},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)

    tracks = []
    for entry in (result.get("entries") or []):
        if not entry:
            continue
        duration = entry.get("duration")
        if duration and int(duration) > MAX_DURATION:
            continue
        track = {
            "id":       entry.get("id", ""),
            "title":    entry.get("title", "Unknown"),
            "uploader": entry.get("uploader") or entry.get("channel") or "Unknown",
            "duration": duration,
            "thumbnail": entry.get("thumbnail") or "",
            "url": f"https://www.youtube.com/watch?v={entry.get('id', '')}",
        }
        music_api.cache_track(track)
        tracks.append(track)
    return tracks[:max_results]


def get_video_info(video_id: str) -> dict:
    """Fetch track metadata by ID (from cache, DB, or YouTube)."""
    cached = music_api.get_cached_track(video_id)
    if cached:
        return cached

    for t in db.get_top(limit=100):
        if t["id"] == video_id and t.get("url"):
            music_api.cache_track(t)
            return t

    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "extractor_args": {"youtube": ["player_client=android"]}}) as ydl:
            info = ydl.extract_info(url, download=False)
        track = {
            "id":       video_id,
            "title":    info.get("title", "Unknown"),
            "uploader": info.get("uploader") or info.get("channel") or "Unknown",
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail") or "",
            "url": url,
        }
        music_api.cache_track(track)
        return track
    except Exception as e:
        logger.error(f"get_video_info: {e}")
        return {}


def download_audio(video_url: str, output_dir: str):
    """Download audio. Tries direct MP3 first, then yt-dlp."""
    if video_url.startswith("http") and (".mp3" in video_url or "/get/" in video_url or ("youtube.com" not in video_url and "youtu.be" not in video_url)):
        try:
            path, ext = music_api.download_direct_mp3(video_url, output_dir)
            if path and os.path.exists(path):
                return path, ext
        except Exception as e:
            logger.warning(f"Direct download failed: {e}, falling back to yt_dlp")

    has_ffmpeg = _has_ffmpeg()
    logger.info(f"ffmpeg: {has_ffmpeg}")

    if has_ffmpeg:
        opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(output_dir, "audio.%(ext)s"),
            "postprocessors": [{"key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3", "preferredquality": "192"}],
            "quiet": False,
            "noplaylist": True,
            "extractor_args": {"youtube": ["player_client=android"]},
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(video_url, download=True)
        mp3 = os.path.join(output_dir, "audio.mp3")
        if os.path.exists(mp3):
            return mp3, "mp3"
        for f in os.listdir(output_dir):
            if f.endswith(".mp3"):
                return os.path.join(output_dir, f), "mp3"

    # No ffmpeg — send native format (m4a/webm)
    opts = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best",
        "outtmpl": os.path.join(output_dir, "audio.%(ext)s"),
        "quiet": False,
        "noplaylist": True,
        "extractor_args": {"youtube": ["player_client=android"]},
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(video_url, download=True)
        ext = info.get("ext", "m4a")

    for f in os.listdir(output_dir):
        fp = os.path.join(output_dir, f)
        if os.path.isfile(fp):
            fext = f.rsplit(".", 1)[-1] if "." in f else ext
            return fp, fext

    return None, None



async def animate_loading(
    message, title: str, uploader: str, duration: str,
    stop_event: asyncio.Event, lang: str
) -> None:
    steps = i18n.loading_steps(lang)
    step_idx = 0
    short = title[:35] + "…" if len(title) > 35 else title
    header = "⏬ *Загружаю трек...*" if lang == "ru" else "⏬ *Loading track...*"

    while not stop_event.is_set():
        filled, empty, pct, status = steps[step_idx % len(steps)]
        bar = "█" * filled + "░" * empty
        text = (
            f"{header}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🎵 *{short}*\n"
            f"👤 {uploader}  •  ⏱ {duration}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"`{bar}` {pct}\n"
            f"{status}"
        )
        try:
            await message.edit_text(text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            pass
        step_idx += 1
        await asyncio.sleep(2.5)


async def recognize_voice(file_path: str) -> dict:
    """Recognize song using ShazamAPI (free, no token)."""
    try:
        from ShazamAPI import Shazam
        with open(file_path, "rb") as f:
            audio_bytes = f.read()
            
        def _shazam_sync():
            shazam = Shazam(audio_bytes)
            recognize_generator = shazam.recognizeSong()
            try:
                result = next(recognize_generator)
                if result and len(result) > 1:
                    data = result[1]
                    if data.get('matches'):
                        return data.get('track')
            except StopIteration:
                pass
            except Exception as e:
                logger.error(f"Shazam parse error: {e}")
            return None

        loop = asyncio.get_event_loop()
        track = await loop.run_in_executor(None, _shazam_sync)
        
        if track:
            # Extract album from sections metadata if available
            album = "—"
            for section in track.get("sections", []):
                if section.get("type") == "SONG":
                    for meta in section.get("metadata", []):
                        if meta.get("title") == "Album":
                            album = meta.get("text", "—")
                            break
            return {
                "title": track.get("title", "Unknown"),
                "artist": track.get("subtitle", "Unknown"),
                "album": album,
            }
    except Exception as e:
        logger.error(f"ShazamAPI error: {e}")
    return {}


# ─────────────────────────────────────────────────────────
# Core Download Processor
# ─────────────────────────────────────────────────────────

async def do_download(
    context: ContextTypes.DEFAULT_TYPE,
    message,
    user_id: int,
    track: dict,
    lang: str,
) -> None:
    """
    Download `track` and send as audio.
    `message` is the Telegram message to animate and edit during the process.
    """
    title       = track["title"]
    uploader    = track.get("uploader", "Unknown")
    url = track.get("url")
    if not url:
        if track.get("id", "").startswith("hm_"):
            found = search_music(f"{uploader} {title}", 1)
            if found:
                url = found[0].get("url")
                track["url"] = url
        else:
            url = f"https://www.youtube.com/watch?v={track['id']}"

    if not url:
        stop_event = asyncio.Event()
        await message.edit_text(i18n.t(lang, "file_not_found"))
        return

    # Cache track for favorites toggle
    context.user_data.setdefault("tracks", {})[track["id"]] = track
    music_api.cache_track(track)

    # ── Start loading animation ───────────────
    stop_event  = asyncio.Event()
    loader_task = asyncio.create_task(
        animate_loading(message, title, uploader, duration_s, stop_event, lang)
    )

    loop = asyncio.get_event_loop()
    with tempfile.TemporaryDirectory() as tmp_dir:

        # ── Download audio ────────────────────
        try:
            audio_path, audio_ext = await loop.run_in_executor(
                None, download_audio, url, tmp_dir
            )
        except Exception as e:
            stop_event.set(); loader_task.cancel()
            logger.error(f"Download error: {e}", exc_info=True)
            await message.edit_text(
                i18n.t(lang, "download_error", str(e)[:200]),
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        if not audio_path or not os.path.exists(audio_path):
            stop_event.set(); loader_task.cancel()
            await message.edit_text(i18n.t(lang, "file_not_found"))
            return

        size_mb = os.path.getsize(audio_path) / 1_048_576
        logger.info(f"Downloaded: {size_mb:.1f}MB  ext={audio_ext}")

        if size_mb > 49:
            stop_event.set(); loader_task.cancel()
            await message.edit_text(i18n.t(lang, "file_too_large"))
            return

        # ── Thumbnail ─────────────────────────
        thumb_path = None
        if track.get("thumbnail"):
            try:
                tp = os.path.join(tmp_dir, "thumb.jpg")
                urllib.request.urlretrieve(track["thumbnail"], tp)
                if os.path.exists(tp):
                    thumb_path = tp
            except Exception:
                pass

        # ── Stop animation ────────────────────
        stop_event.set()
        loader_task.cancel()

        # ── Send audio ────────────────────────
        caption = i18n.t(lang, "caption", title, uploader, duration_s)
        fav_label = i18n.t(lang, "fav_btn_rm" if db.is_fav(user_id, track["id"]) else "fav_btn_add")
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(fav_label, callback_data=f"fav:{track['id']}"),
        ]])
        
        try:
            audio_fh = open(audio_path, "rb")
            kwargs = dict(
                chat_id=message.chat_id,
                audio=audio_fh,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                title=title,
                performer=uploader,
                duration=track.get("duration"),
                write_timeout=300,
                read_timeout=60,
                reply_markup=keyboard,
            )
            if thumb_path:
                kwargs["thumbnail"] = open(thumb_path, "rb")
            await context.bot.send_audio(**kwargs)
            audio_fh.close()
            if "thumbnail" in kwargs and hasattr(kwargs["thumbnail"], "close"):
                kwargs["thumbnail"].close()
        except Exception as e:
            logger.error(f"Send error: {e}", exc_info=True)
            await message.edit_text(
                i18n.t(lang, "send_error", str(e)[:200]),
                parse_mode=ParseMode.MARKDOWN,
            )
            return

    # ── Update DB ─────────────────────────────
    db.add_history(user_id, track)
    db.update_stats(track)

    try:
        await message.delete()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────
# Command Handlers
# ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.ensure_user(user.id, user.username or "")
    lang = db.get_lang(user.id)

    # Deep link from inline mode: /start dl_VIDEO_ID
    if context.args and context.args[0].startswith("dl_"):
        video_id = context.args[0][3:]
        msg = await update.message.reply_text("⏳", parse_mode=ParseMode.MARKDOWN)
        loop = asyncio.get_event_loop()
        track = await loop.run_in_executor(None, get_video_info, video_id)
        if not track:
            await msg.edit_text(i18n.t(lang, "info_not_found"))
            return
        await do_download(context, msg, user.id, track, lang)
        return

    # Normal /start -> Language selection
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🇷🇺 Русский", callback_data="start_lang:ru"),
        InlineKeyboardButton("🇬🇧 English",  callback_data="start_lang:en"),
    ]])
    await update.message.reply_text(
        i18n.t(lang, "lang_first"), parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.ensure_user(user.id, user.username or "")
    lang = db.get_lang(user.id)
    await update.message.reply_text(i18n.t(lang, "help"), parse_mode=ParseMode.MARKDOWN)


async def cmd_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.ensure_user(user.id, user.username or "")
    lang = db.get_lang(user.id)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton("🇬🇧 English",  callback_data="lang:en"),
    ]])
    await update.message.reply_text(
        i18n.t(lang, "lang_select"), parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard
    )


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.ensure_user(user.id, user.username or "")
    lang = db.get_lang(user.id)

    tracks = db.get_history(user.id)
    if not tracks:
        await update.message.reply_text(i18n.t(lang, "history_empty"), parse_mode=ParseMode.MARKDOWN)
        return

    text = i18n.t(lang, "history_header")
    row, buttons = [], []
    for idx, track in enumerate(tracks, 1):
        dur = fmt_duration(track["duration"])
        text += i18n.t(lang, "track_num", idx, track["title"][:40], track["uploader"][:25], dur, track.get("count", 1))
        track_url = track.get("url") or (f"https://www.youtube.com/watch?v={track['id']}" if not str(track['id']).startswith("hm_") else "")
        track_data = {**track, "url": track_url}
        context.user_data.setdefault("tracks", {})[track["id"]] = track_data
        music_api.cache_track(track_data)
        row.append(InlineKeyboardButton(f"▶️ {idx}", callback_data=f"hd:{track['id']}"))
        if len(row) == 5:
            buttons.append(row); row = []
    if row:
        buttons.append(row)

    await update.message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons)
    )


async def cmd_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.ensure_user(user.id, user.username or "")
    lang = db.get_lang(user.id)
    await _send_favorites(update.message, context, user.id, lang, edit=False)


async def _send_favorites(msg_or_query, context, user_id: int, lang: str, edit: bool) -> None:
    tracks = db.get_favorites(user_id)
    if not tracks:
        text = i18n.t(lang, "fav_empty")
        if edit:
            await msg_or_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)
        else:
            await msg_or_query.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        return

    text = i18n.t(lang, "fav_header", len(tracks))
    buttons = []
    for idx, track in enumerate(tracks, 1):
        dur = fmt_duration(track["duration"])
        text += i18n.t(lang, "track_num", idx, track["title"][:40], track["uploader"][:25], dur, track.get("count", 0))
        track_url = track.get("url") or (f"https://www.youtube.com/watch?v={track['id']}" if not str(track['id']).startswith("hm_") else "")
        track_data = {**track, "url": track_url}
        context.user_data.setdefault("tracks", {})[track["id"]] = track_data
        music_api.cache_track(track_data)
        label = track["title"][:28] + "…" if len(track["title"]) > 28 else track["title"]
        buttons.append([
            InlineKeyboardButton(f"▶️ {idx}. {label}", callback_data=f"fd:{track['id']}"),
            InlineKeyboardButton("💔", callback_data=f"fr:{track['id']}"),
        ])

    keyboard = InlineKeyboardMarkup(buttons)
    if edit:
        await msg_or_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    else:
        await msg_or_query.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.ensure_user(user.id, user.username or "")
    lang = db.get_lang(user.id)

    tracks = db.get_top()
    if not tracks:
        await update.message.reply_text(i18n.t(lang, "top_empty"), parse_mode=ParseMode.MARKDOWN)
        return

    text = i18n.t(lang, "top_header")
    buttons = []
    for idx, t in enumerate(tracks, 1):
        dur = fmt_duration(t["duration"])
        text += i18n.t(lang, "track_num", idx, t["title"][:40], t["uploader"][:25], dur, t.get("count", 1))
        # Add to local cache so user can download from top
        track_url = t.get("url") or (f"https://www.youtube.com/watch?v={t['id']}" if not str(t['id']).startswith("hm_") else "")
        track_data = {**t, "url": track_url}
        context.user_data.setdefault("tracks", {})[t["id"]] = track_data
        music_api.cache_track(track_data)
        
        # Add inline button for download
        buttons.append(InlineKeyboardButton(str(idx), callback_data=f"hd:{t['id']}"))
    
    # Chunk buttons
    keyboard = InlineKeyboardMarkup([buttons[i:i + 5] for i in range(0, len(buttons), 5)])
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)


# ─────────────────────────────────────────────────────────
# Unified Callback Handler
# ─────────────────────────────────────────────────────────

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q    = update.callback_query
    await q.answer()
    uid  = update.effective_user.id
    db.ensure_user(uid)
    lang = db.get_lang(uid)
    data = q.data

    # ── Language (First time) ────────────────
    if data.startswith("start_lang:"):
        new_lang = data[11:]
        db.set_lang(uid, new_lang)
        try:
            await q.message.delete()
        except Exception:
            pass
        reply_markup = get_main_menu(new_lang)
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=i18n.t(new_lang, "welcome"),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return

    # ── Language (Change later) ──────────────
    if data.startswith("lang:"):
        new_lang = data[5:]
        db.set_lang(uid, new_lang)
        key = "lang_set_ru" if new_lang == "ru" else "lang_set_en"
        try:
            await q.message.delete()
        except Exception:
            pass
        # Update keyboard language without showing welcome again
        reply_markup = get_main_menu(new_lang)
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=i18n.t(new_lang, key),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return

    # ── Favorite toggle (from success message) ─
    if data.startswith("fav:"):
        video_id = data[4:]
        track = context.user_data.get("tracks", {}).get(video_id)
        if not track:
            await q.answer("Track not found in cache", show_alert=True)
            return
        result = db.toggle_favorite(uid, track)
        if result == "added":
            await q.answer(i18n.t(lang, "fav_added"))
            new_label = i18n.t(lang, "fav_btn_rm")
        elif result == "removed":
            await q.answer(i18n.t(lang, "fav_removed"))
            new_label = i18n.t(lang, "fav_btn_add")
        else:
            await q.answer(i18n.t(lang, "fav_limit"), show_alert=True)
            return
        try:
            await q.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(new_label, callback_data=f"fav:{video_id}")
                ]])
            )
        except Exception:
            pass
        return

    # ── Remove from favorites list ────────────
    if data.startswith("fr:"):
        video_id = data[3:]
        track = context.user_data.get("tracks", {}).get(video_id, {"id": video_id, "title": ""})
        db.toggle_favorite(uid, track)
        await q.answer(i18n.t(lang, "fav_removed"))
        await _send_favorites(q, context, uid, lang, edit=True)
        return

    # ── Download from search results ──────────
    if data.startswith("dl:"):
        video_id = data[3:]
        track = context.user_data.get("tracks", {}).get(video_id)
        if not track:
            await q.edit_message_text(i18n.t(lang, "info_not_found"))
            return
        await do_download(context, q.message, uid, track, lang)
        return

    # ── Download from history ─────────────────
    if data.startswith("hd:"):
        video_id = data[3:]
        track = context.user_data.get("tracks", {}).get(video_id)
        if not track:
            loop = asyncio.get_event_loop()
            track = await loop.run_in_executor(None, get_video_info, video_id)
        if not track:
            await q.answer(i18n.t(lang, "info_not_found"), show_alert=True)
            return
        msg = await context.bot.send_message(q.message.chat_id, "⏳")
        await do_download(context, msg, uid, track, lang)
        return

    # ── Download from favorites ───────────────
    if data.startswith("fd:"):
        video_id = data[3:]
        track = context.user_data.get("tracks", {}).get(video_id)
        if not track:
            loop = asyncio.get_event_loop()
            track = await loop.run_in_executor(None, get_video_info, video_id)
        if not track:
            await q.answer(i18n.t(lang, "info_not_found"), show_alert=True)
            return
        msg = await context.bot.send_message(q.message.chat_id, "⏳")
        await do_download(context, msg, uid, track, lang)
        return


# ─────────────────────────────────────────────────────────
# Message Handlers
# ─────────────────────────────────────────────────────────

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    db.ensure_user(user.id, user.username or "")
    lang = db.get_lang(user.id)
    query = update.message.text.strip()
    if not query:
        return

    # Intercept menu buttons
    if query in (i18n.t("ru", "menu_history"), i18n.t("en", "menu_history")):
        return await cmd_history(update, context)
    if query in (i18n.t("ru", "menu_favorites"), i18n.t("en", "menu_favorites")):
        return await cmd_favorites(update, context)
    if query in (i18n.t("ru", "menu_top"), i18n.t("en", "menu_top")):
        return await cmd_top(update, context)
    if query in (i18n.t("ru", "menu_lang"), i18n.t("en", "menu_lang")):
        return await cmd_lang(update, context)
    if query in (i18n.t("ru", "menu_help"), i18n.t("en", "menu_help")):
        return await cmd_help(update, context)

    searching_msg = await update.message.reply_text(
        i18n.t(lang, "searching", query), parse_mode=ParseMode.MARKDOWN
    )
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    loop = asyncio.get_event_loop()
    try:
        tracks = await loop.run_in_executor(None, search_music, query)
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        await searching_msg.edit_text(i18n.t(lang, "search_error"))
        return

    if not tracks:
        await searching_msg.edit_text(i18n.t(lang, "no_results"))
        return

    context.user_data.setdefault("tracks", {})
    for track in tracks:
        context.user_data["tracks"][track["id"]] = track

    text = i18n.t(lang, "results_header", query)
    buttons = []
    for idx, track in enumerate(tracks, 1):
        dur = fmt_duration(track["duration"])
        text += i18n.t(lang, "track_num", idx, track["title"], track["uploader"], dur, track.get("count", 0))
        label = track["title"][:38] + "…" if len(track["title"]) > 38 else track["title"]
        buttons.append([
            InlineKeyboardButton(f"▶️ {idx}. {label}  [{dur}]", callback_data=f"dl:{track['id']}")
        ])

    await searching_msg.edit_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(buttons)
    )


async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recognize song from voice/audio message using ShazamAPI."""
    user = update.effective_user
    db.ensure_user(user.id, user.username or "")
    lang = db.get_lang(user.id)

    msg = await update.message.reply_text(
        i18n.t(lang, "voice_searching"), parse_mode=ParseMode.MARKDOWN
    )
    voice = update.message.voice or update.message.audio
    if not voice:
        return
        
    if hasattr(voice, "duration") and voice.duration > 30:
        await msg.edit_text(
            "⏳ " + ("Аудио слишком длинное (макс. 30 сек)" if lang == "ru" else "Audio too long (max 30s)")
        )
        return

    try:
        with tempfile.TemporaryDirectory() as tmp:
            vf = await context.bot.get_file(voice.file_id, read_timeout=60, connect_timeout=60)
            path = os.path.join(tmp, "voice.ogg")
            await vf.download_to_drive(path)
            result = await recognize_voice(path)
    except Exception as e:
        logger.error(f"Voice handler error: {e}", exc_info=True)
        await msg.edit_text(i18n.t(lang, "voice_error"))
        return

    if not result:
        await msg.edit_text(i18n.t(lang, "voice_not_found"))
        return

    song   = result.get("title", "Unknown")
    artist = result.get("artist", "Unknown")
    album  = result.get("album") or "—"
    
    # Try to search for the found track to get a download link
    query = f"{artist} {song}"
    loop = asyncio.get_event_loop()
    try:
        tracks = await loop.run_in_executor(None, search_music, query, 1)
    except Exception:
        tracks = []
        
    if tracks:
        track = tracks[0]
        context.user_data.setdefault("tracks", {})[track["id"]] = track
        music_api.cache_track(track)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(i18n.t(lang, "download_btn"), callback_data=f"dl:{track['id']}")
        ]])
        await msg.edit_text(
            i18n.t(lang, "voice_found", song, artist, album),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    else:
        await msg.edit_text(
            i18n.t(lang, "voice_found", song, artist, album),
            parse_mode=ParseMode.MARKDOWN
        )


# ─────────────────────────────────────────────────────────
# Inline Query Handler
# ─────────────────────────────────────────────────────────

async def on_inline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query_text = (update.inline_query.query or "").strip()
    if len(query_text) < 2:
        return

    loop = asyncio.get_event_loop()
    try:
        tracks = await loop.run_in_executor(None, search_music, query_text, 5)
    except Exception:
        return

    results = []
    for track in tracks:
        dur   = fmt_duration(track["duration"])
        title = track["title"]
        deep  = f"https://t.me/{BOT_USERNAME}?start=dl_{track['id']}"

        content = (
            f"🎵 *{title}*\n"
            f"👤 {track['uploader']}  •  ⏱ {dur}\n\n"
            f"⬇️ [Скачать в Tunova]({deep})"
        )
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=title[:60],
                description=f"👤 {track['uploader']} • ⏱ {dur}",
                input_message_content=InputTextMessageContent(
                    content, parse_mode=ParseMode.MARKDOWN
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬇️ Скачать в Tunova", url=deep)
                ]]),
                thumbnail_url=track.get("thumbnail") or None,
            )
        )

    await update.inline_query.answer(results, cache_time=30)


# ─────────────────────────────────────────────────────────
# Error Handler
# ─────────────────────────────────────────────────────────

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Exception: {context.error}", exc_info=context.error)


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────

from aiohttp import web

async def start_dummy_server():
    """Starts a dummy web server to satisfy Render's port binding requirement."""
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get('/', lambda request: web.Response(text="Bot is running!"))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Dummy web server started on port {port}")


async def post_init(application: Application) -> None:
    from telegram import BotCommand
    commands = [
        BotCommand("start", "🏠 Главное меню (Main)"),
        BotCommand("history", "🕒 Последние 10 треков (History)"),
        BotCommand("favorites", "❤️ Избранное (Favorites)"),
        BotCommand("top", "📊 Топ-10 треков (Top-10)"),
        BotCommand("lang", "🌐 Язык (Language)"),
        BotCommand("help", "ℹ️ Помощь (Help)"),
    ]
    await application.bot.set_my_commands(commands)
    
    # Start the dummy web server in the background for Render
    if os.environ.get("RENDER"):
        asyncio.create_task(start_dummy_server())

def main() -> None:
    db.init_db()

    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Commands
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("lang",      cmd_lang))
    app.add_handler(CommandHandler("history",   cmd_history))
    app.add_handler(CommandHandler("favorites", cmd_favorites))
    app.add_handler(CommandHandler("top",       cmd_top))

    # Callbacks & inline
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(InlineQueryHandler(on_inline))

    # Messages
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    app.add_error_handler(on_error)

    logger.info(f"🎵 {BOT_NAME} (@{BOT_USERNAME}) is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
