import asyncio
import os
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from PIL import Image
from dotenv import load_dotenv
from aiohttp import web

# Импортируем наши новые модули для работы с БД и кнопками
import database as db
import keyboards as kb
from downloader import download_soundcloud_track

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализируем базу данных при запуске скрипта
db.init_db()


# Описываем состояния для FSM (ожидание ввода от пользователя)
class PlaylistStates(StatesGroup):
    waiting_for_playlist_name = State()


def process_thumbnail(image_path: str):
    """Обрезает картинку до квадрата и сжимает до 300x300 для идеального превью в TG"""
    with Image.open(image_path) as img:
        if img.mode != 'RGB':
            img = img.convert('RGB')

        min_side = min(img.size)
        left = (img.width - min_side) // 2
        top = (img.height - min_side) // 2
        right = left + min_side
        bottom = top + min_side

        img = img.crop((left, top, right, bottom))
        img = img.resize((300, 300), Image.Resampling.LANCZOS)
        img.save(image_path, "JPEG", quality=85)


# --- ОБРАБОТКА КОМАНД ---

@dp.message(Command("start"))
@dp.message(Command("menu"))
async def start_cmd(message: types.Message):
    # Регистрируем пользователя в БД, если его там нет
    db.add_user(message.from_user.id)

    await message.answer(
        f"Привет, {message.from_user.first_name}! 🎵\n\n"
        "• Чтобы скачать трек, просто **отправь мне ссылку** на SoundCloud.\n"
        "• Для управления треками используй меню ниже:",
        reply_markup=kb.get_main_menu(),
        parse_mode="Markdown"
    )


# --- ОБРАБОТКА ИНЛАЙН-КНОПОК (CALLBACK QUERIES) ---

@dp.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()  # Сбрасываем состояния, если пользователь вернулся в меню
    await callback.message.edit_text(
        "🎵 Главное меню бота.\nПросто отправь мне ссылку на SoundCloud или выбери действие:",
        reply_markup=kb.get_main_menu()
    )
    await callback.answer()


@dp.callback_query(F.data == "view_playlists")
async def view_playlists_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    playlists = db.get_user_playlists(user_id)

    if not playlists:
        await callback.message.edit_text(
            "У тебя пока нет созданных плейлистов. Давай создадим первый?",
            reply_markup=kb.get_main_menu()
        )
    else:
        await callback.message.edit_text(
            "🗂 Твои плейлисты:",
            reply_markup=kb.get_playlists_keyboard(playlists)
        )
    await callback.answer()


@dp.callback_query(F.data == "create_playlist")
async def create_playlist_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📝 Введи название для нового плейлиста:")
    # Включаем режим ожидания текста от пользователя
    await state.set_state(PlaylistStates.waiting_for_playlist_name)
    await callback.answer()


# ИСПРАВЛЕНО: Метод startswith вместо start_with
@dp.callback_query(F.data.startswith("pl_"))
async def view_single_playlist(callback: CallbackQuery):
    playlist_id = int(callback.data.split("_")[1])
    tracks = db.get_playlist_tracks(playlist_id)

    if not tracks:
        text = "🏜 Этот плейлист пока пуст.\n\nЧтобы добавить трек, сначала скачай его, отправив мне ссылку!"
    else:
        text = "🎵 Треки в этом плейлисте:\n\n"
        for i, (title, artist, url) in enumerate(tracks, 1):
            text += f"{i}. **{artist}** — {title}\n🔗 [Слушать на SC]({url})\n\n"

    # Добавляем кнопку возврата к списку плейлистов
    builder = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ К плейлистам", callback_data="view_playlists")]
    ])

    await callback.message.edit_text(text, reply_markup=builder, parse_mode="Markdown", disable_web_page_preview=True)
    await callback.answer()


@dp.callback_query(F.data == "help_info")
async def help_handler(callback: CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ **Как пользоваться ботом:**\n\n"
        "1. Скопируй ссылку на трек из приложения или сайта SoundCloud.\n"
        "2. Вставь её в чат с ботом.\n"
        "3. Бот пришлёт тебе аудиофайл с оригинальной обложкой и тегами.\n"
        "4. Под треком будет кнопка, позволяющая сохранить его в плейлист внутри бота!",
        reply_markup=kb.get_main_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()


# --- ОБРАБОТКА ТЕКСТА (FSM И ССЫЛКИ) ---

@dp.message(PlaylistStates.waiting_for_playlist_name)
async def process_playlist_creation(message: types.Message, state: FSMContext):
    playlist_name = message.text.strip()

    if len(playlist_name) > 30:
        await message.answer("❌ Название слишком длинное (максимум 30 символов). Попробуй ещё раз:")
        return

    db.create_playlist(message.from_user.id, playlist_name)
    await state.clear()  # Выключаем режим ожидания

    await message.answer(
        f"✅ Плейлист **«{playlist_name}»** успешно создан!",
        reply_markup=kb.get_main_menu(),
        parse_mode="Markdown"
    )


@dp.message()
async def handle_link(message: types.Message):
    url = message.text.strip()

    if "soundcloud.com" not in url:
        await message.answer("Отправь мне корректную ССЫЛКУ на SoundCloud или используй /menu")
        return

    status_msg = await message.answer("⚡ Разбираю ссылку и скачиваю трек...")

    try:
        # 1. Скачиваем трек через твой downloader.py
        track_data = await download_soundcloud_track(url)
        audio_file = FSInputFile(track_data['file_path'])

        # 2. Безопасно скачиваем и обрабатываем обложку
        thumb_path = None
        thumbnail_url = track_data.get('thumbnail_url')

        if thumbnail_url:
            try:
                thumb_path = track_data['file_path'] + ".jpg"
                async with httpx.AsyncClient() as client:
                    response = await client.get(thumbnail_url)
                    if response.status_code == 200:
                        with open(thumb_path, "wb") as f:
                            f.write(response.content)

                        process_thumbnail(thumb_path)
            except Exception as thumb_err:
                print(f"Не удалось создать обложку: {thumb_err}")
                thumb_path = None

        # 3. Готовим превью к отправке
        tg_thumb = FSInputFile(thumb_path) if thumb_path and os.path.exists(thumb_path) else None

        # 4. Отправляем в Telegram с кнопкой добавления в плейлист
        playlists = db.get_user_playlists(message.from_user.id)

        # Передаем инлайн-кнопку под трек
        await message.answer_audio(
            audio=audio_file,
            title=track_data['title'],
            performer=track_data['artist'],
            duration=track_data['duration'],
            thumbnail=tg_thumb,
            reply_markup=kb.get_track_options_keyboard(url, playlists)
        )

        # Подчищаем локальные файлы за собой
        if os.path.exists(track_data['file_path']):
            os.remove(track_data['file_path'])
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)

        await status_msg.delete()

    except Exception as e:
        print(f"Ошибка при обработке ссылки: {e}")
        await status_msg.edit_text("❌ Не удалось скачать этот трек. Возможно, он скрыт или удален.")


# --- СВЯЗУЮЩИЙ ХЕНДЛЕР ДЛЯ ДОБАВЛЕНИЯ ТРЕКА В ПЛЕЙЛИСТ ---
@dp.callback_query(F.data == "add_to_pl_select")
async def choose_playlist_for_track(callback: CallbackQuery):
    playlists = db.get_user_playlists(callback.from_user.id)
    if not playlists:
        await callback.answer("У тебя еще нет плейлистов. Создай их через /menu!", show_alert=True)
        return

    # Динамически собираем кнопки с плейлистами специально для сохранения трека
    builder = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=f"📁 {name}", callback_data=f"save_{pl_id}")] for pl_id, name in playlists
    ])

    # Вытаскиваем инфу о треке для красоты сообщения выбора
    audio_info = ""
    if callback.message.audio:
        audio_info = f"{callback.message.audio.performer} - {callback.message.audio.title}"

    # Отправляем новое сообщение-выбор реплаем на аудио-плеер
    await callback.message.reply(
        f"📥 В какой плейлист сохранить этот трек?\n`{audio_info}`",
        reply_markup=builder,
        parse_mode="Markdown"
    )
    await callback.answer()


# ИСПРАВЛЕНО: Метод startswith вместо start_with + Полная переработка логики поиска аудиоданных
@dp.callback_query(F.data.startswith("save_"))
async def save_track_to_db(callback: CallbackQuery):
    playlist_id = int(callback.data.split("_")[1])

    title = "Без названия"
    artist = "Неизвестный исполнитель"
    url = "https://soundcloud.com"

    # Безопасно ищем объект аудио в сообщении-родители или в реплае
    audio_source = None
    if callback.message.reply_to_message and callback.message.reply_to_message.audio:
        audio_source = callback.message.reply_to_message.audio
    elif callback.message.audio:
        audio_source = callback.message.audio

    if audio_source:
        title = audio_source.title or title
        artist = audio_source.performer or artist

    try:
        db.add_track_to_playlist(playlist_id, title, artist, url)
        await callback.message.edit_text(f"✅ Трек **{artist} — {title}** успешно добавлен!", parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка при сохранении трека в БД: {e}")
        await callback.message.edit_text("❌ Ошибка: Не удалось сохранить трек в базу данных.")

    await callback.answer()


# --- ВЕБ-СЕРВЕР ДЛЯ ХОСТИНГА (RENDER PING) ---
async def handle_ping(request):
    return web.Response(text="Bot is running!")


# --- ЗАПУСК БОТА И ВЕБ-СЕРВЕРА ---
async def main():
    print("🚀 Бот успешно запущен и готов к работе с плейлистами!")

    # 1. Запуск веб-сервера на порту 10000 для Render
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    asyncio.create_task(site.start())  # Запускаем фоновой задачей

    # 2. Запуск long polling бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    from aiohttp import web  # Убедись, что импорт на месте

    asyncio.run(main())