"""Translations for Tunova bot — Russian / English."""

_STRINGS: dict = {
    "ru": {
        "lang_first": (
            "🌐 *Выберите язык / Select language*\n\n"
            "_Для продолжения выберите язык._\n"
            "_Please select your language._"
        ),
        "menu_search":    "🔍 Поиск",
        "menu_history":   "📋 История",
        "menu_favorites": "❤️ Избранное",
        "menu_top":       "📊 Топ-10",
        "menu_lang":      "🌐 Язык",
        "menu_help":      "ℹ️ Помощь",
        "search_prompt":  "🔍 *Поиск музыки*\n\nНапишите название песни или исполнителя 👇",
        "welcome": (
            "🎵 *Добро пожаловать в Tunova!*\n\n"
            "Напишите название песни или исполнителя — "
            "я найду и отправлю аудио прямо сюда.\n\n"
            "📌 *Пример:* `Imagine Dragons Believer`\n"
            "⚡ Максимум: 10 минут\n\n"
            "💡 Работает в любом чате: `@Tunova_Bot <запрос>`"
        ),
        "help": (
            "ℹ️ *Как пользоваться Tunova:*\n\n"
            "1️⃣ Напишите название или исполнителя\n"
            "2️⃣ Выберите трек из списка\n"
            "3️⃣ Получите MP3 прямо в чате\n"
            "❤️ Нажмите сердечко — сохраните в избранное\n\n"
            "🎙️ Отправьте голосовое — распознаю песню! (макс. 30 сек)"
        ),
        "searching":       "🔍 Ищу: *{}*...",
        "no_results":      "😔 Ничего не найдено. Попробуйте другой запрос.",
        "search_error":    "❌ Ошибка поиска. Попробуйте ещё раз.",
        "results_header":  "🎵 *Результаты:* `{}`\n\n",
        "track_num":       "{}. *{}*\n   👤 {} | ⏱ {} | ⬇️ {}x\n\n",
        "download_error":  "❌ Ошибка скачивания:\n`{}`",
        "file_not_found":  "❌ Файл не найден. Попробуйте другой трек.",
        "file_too_large":  "❌ Файл >50 МБ — слишком большой.",
        "send_error":      "❌ Не удалось отправить:\n`{}`",
        "sent":            "✅ *{}* — готово!\n\n🔍 Напишите ещё одно название для поиска.",
        "caption":         "🎵 *{}*\n👤 {}\n⏱ {}\n\n🤖 @Tunova\_Bot",
        "fav_btn_add":     "❤️ В избранное",
        "fav_btn_rm":      "💔 Убрать из избранного",
        "fav_added":       "❤️ Добавлено в избранное!",
        "fav_removed":     "💔 Удалено из избранного.",
        "fav_limit":       "⚠️ Избранное заполнено (макс. 20). Удалите что-нибудь: /favorites",
        "fav_empty":       "📭 *Избранное пусто.*\n\nСкачайте трек и нажмите ❤️ чтобы сохранить.",
        "fav_header":      "❤️ *Ваше избранное* ({} трек(ов)):\n\n",
        "history_empty":   "📭 *История пуста.* Скачайте первый трек!",
        "history_header":  "🕐 *Последние треки:*\n\n",
        "top_empty":       "📊 Статистика пуста. Скачайте треки!",
        "top_header":      "📊 *Топ-10 треков:*\n\n",
        "lang_select":     "🌐 *Выберите язык:*",
        "lang_set_ru":     "✅ Язык: *Русский* 🇷🇺",
        "lang_set_en":     "✅ Language: *English* 🇬🇧",
        "info_not_found":  "❌ Трек не найден. Попробуйте поиск заново.",
        "voice_searching": "🎧 Распознаю мелодию...",
        "voice_found": (
            "🎵 *Найдено!*\n\n"
            "🎤 *{}*\n"
            "👤 {}\n"
            "💿 {}"
        ),
        "voice_not_found": "😔 Не удалось распознать. Попробуйте другой фрагмент.",
        "voice_error":     "❌ Ошибка при распознавании.",
        "voice_no_api":    "⚠️ Распознавание недоступно.\nДобавьте `AUDD_TOKEN=...` в файл `.env`",
        "download_btn":    "⬇️ Скачать в Tunova",
        "loading_header":  "⏬ *Загружаю трек...*",
        "loading_steps": [
            (0,  10, " 0%", "🔍 Подбираю трек..."),
            (2,  8,  "20%", "⤵️  Нашёл! Начинаю загрузку..."),
            (4,  6,  "40%", "⏬  Скачиваю аудио..."),
            (5,  5,  "50%", "⏬  Скачиваю аудио..."),
            (7,  3,  "70%", "🎛️  Обрабатываю звук..."),
            (8,  2,  "85%", "🎵  Конвертирую в MP3..."),
            (9,  1,  "95%", "📤  Отправляю в Telegram..."),
            (10, 0,  "99%", "📤  Загружаю в Telegram..."),
        ],
    },
    "en": {
        "lang_first": (
            "🌐 *Выберите язык / Select language*\n\n"
            "_Для продолжения выберите язык._\n"
            "_Please select your language._"
        ),
        "menu_search":    "🔍 Search",
        "menu_history":   "📋 History",
        "menu_favorites": "❤️ Favorites",
        "menu_top":       "📊 Top-10",
        "menu_lang":      "🌐 Language",
        "menu_help":      "ℹ️ Help",
        "search_prompt":  "🔍 *Music Search*\n\nType a song name or artist 👇",
        "welcome": (
            "🎵 *Welcome to Tunova!*\n\n"
            "Type a song name or artist — "
            "I'll find and send the audio right here.\n\n"
            "📌 *Example:* `Imagine Dragons Believer`\n"
            "⚡ Max length: 10 minutes\n\n"
            "💡 Works in any chat: `@Tunova_Bot <query>`"
        ),
        "help": (
            "ℹ️ *How to use Tunova:*\n\n"
            "1️⃣ Write a song name or artist\n"
            "2️⃣ Pick a track from the list\n"
            "3️⃣ Get the MP3 right in chat\n"
            "❤️ Press heart — save to favorites\n\n"
            "🎙️ Send a voice message — I'll recognize it! (max 30 sec)"
        ),
        "searching":       "🔍 Searching: *{}*...",
        "no_results":      "😔 Nothing found. Try a different query.",
        "search_error":    "❌ Search error. Please try again.",
        "results_header":  "🎵 *Results for:* `{}`\n\n",
        "track_num":       "{}. *{}*\n   👤 {} | ⏱ {} | ⬇️ {}x\n\n",
        "download_error":  "❌ Download error:\n`{}`",
        "file_not_found":  "❌ File not found. Try another track.",
        "file_too_large":  "❌ File >50 MB — too large.",
        "send_error":      "❌ Failed to send:\n`{}`",
        "sent":            "✅ *{}* — done!\n\n🔍 Type another name to find more music.",
        "caption":         "🎵 *{}*\n👤 {}\n⏱ {}\n\n🤖 @Tunova\_Bot",
        "fav_btn_add":     "❤️ Add to favorites",
        "fav_btn_rm":      "💔 Remove from favorites",
        "fav_added":       "❤️ Added to favorites!",
        "fav_removed":     "💔 Removed from favorites.",
        "fav_limit":       "⚠️ Favorites full (max 20). Remove something: /favorites",
        "fav_empty":       "📭 *Favorites is empty.*\n\nDownload a track and press ❤️ to save.",
        "fav_header":      "❤️ *Your favorites* ({} track(s)):\n\n",
        "history_empty":   "📭 *History is empty.* Download your first track!",
        "history_header":  "🕐 *Recent tracks:*\n\n",
        "top_empty":       "📊 Statistics empty. Download some tracks!",
        "top_header":      "📊 *Top-10 tracks:*\n\n",
        "lang_select":     "🌐 *Select language:*",
        "lang_set_ru":     "✅ Язык: *Русский* 🇷🇺",
        "lang_set_en":     "✅ Language: *English* 🇬🇧",
        "info_not_found":  "❌ Track not found. Try searching again.",
        "voice_searching": "🎧 Recognizing melody...",
        "voice_found": (
            "🎵 *Found!*\n\n"
            "🎤 *{}*\n"
            "👤 {}\n"
            "💿 {}"
        ),
        "voice_not_found": "😔 Could not recognize the melody. Try another fragment.",
        "voice_error":     "❌ Recognition error.",
        "voice_no_api":    "⚠️ Recognition unavailable.\nAdd `AUDD_TOKEN=...` to your `.env` file.",
        "download_btn":    "⬇️ Download in Tunova",
        "loading_header":  "⏬ *Loading track...*",
        "loading_steps": [
            (0,  10, " 0%", "🔍 Looking up track..."),
            (2,  8,  "20%", "⤵️  Found! Starting download..."),
            (4,  6,  "40%", "⏬  Downloading audio..."),
            (5,  5,  "50%", "⏬  Downloading audio..."),
            (7,  3,  "70%", "🎛️  Processing audio..."),
            (8,  2,  "85%", "🎵  Converting to MP3..."),
            (9,  1,  "95%", "📤  Sending to Telegram..."),
            (10, 0,  "99%", "📤  Uploading to Telegram..."),
        ],
    },
}


def t(lang: str, key: str, *args) -> str:
    """Get translated string, optionally formatted with args."""
    strings = _STRINGS.get(lang, _STRINGS["ru"])
    text = strings.get(key, _STRINGS["ru"].get(key, key))
    if args:
        try:
            return text.format(*args)
        except Exception:
            return text
    return text


def loading_steps(lang: str) -> list:
    strings = _STRINGS.get(lang, _STRINGS["ru"])
    return strings.get("loading_steps", _STRINGS["ru"]["loading_steps"])
