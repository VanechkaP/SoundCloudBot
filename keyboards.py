from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎵 Мои Плейлисты", callback_data="view_playlists"),
        InlineKeyboardButton(text="➕ Создать плейлист", callback_data="create_playlist")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help_info")
    )
    return builder.as_markup()


def get_playlists_keyboard(playlists) -> InlineKeyboardMarkup:
    """Генерирует список кнопок с плейлистами пользователя"""
    builder = InlineKeyboardBuilder()

    for playlist_id, name in playlists:
        # При клике на плейлист отправляем его ID
        builder.row(InlineKeyboardButton(text=f"📂 {name}", callback_data=f"pl_{playlist_id}"))

    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu"))
    return builder.as_markup()


def get_track_options_keyboard(url: str, playlists) -> InlineKeyboardMarkup:
    """Кнопки под скачанным треком, позволяющие добавить его в плейлист"""
    builder = InlineKeyboardBuilder()

    # Кодируем экшен добавления (в реальном проекте лучше использовать CallbackData,
    # но для простоты пока сделаем через компактные строки)
    builder.row(InlineKeyboardButton(text="➕ Добавить в плейлист", callback_data="add_to_pl_select"))
    return builder.as_markup()