import asyncio
import os
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder


# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = 6502304303

DB_NAME = "anime.db"


# =========================
# БОТ И DISPATCHER
# =========================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================
# СОСТОЯНИЯ
# =========================

class AddAnimeState(StatesGroup):
    title = State()


class AddEpisodeState(StatesGroup):
    anime_id = State()
    season = State()
    episode = State()
    video = State()


# =========================
# БАЗА
# =========================

async def init_db():

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS anime (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anime_id INTEGER NOT NULL,
                season_number INTEGER NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER NOT NULL,
                episode_number INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                UNIQUE(season_id, episode_number)
            )
        """)

        await db.commit()


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

def main_menu():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="📚 Каталог",
        callback_data="catalog"
    )

    builder.button(
        text="🔎 Поиск",
        callback_data="search"
    )

    builder.adjust(1)

    return builder.as_markup()


# =========================
# АДМИН МЕНЮ
# =========================

def admin_menu():

    builder = InlineKeyboardBuilder()

    builder.button(
        text="➕ Добавить аниме",
        callback_data="add_anime"
    )

    builder.button(
        text="➕ Добавить серию",
        callback_data="add_episode"
    )

    builder.button(
        text="🗑 Удалить аниме",
        callback_data="delete_anime"
    )

    builder.button(
        text="📚 Каталог",
        callback_data="catalog"
    )

    builder.adjust(1)

    return builder.as_markup()


# =========================
# START
# =========================

@dp.message(Command("start"))
async def start(message: Message):

    await message.answer(
        "🎌 <b>Добро пожаловать!</b>\n\n"
        "Выбери нужный раздел:",
        reply_markup=main_menu()
    )


# =========================
# ADMIN
# =========================

@dp.message(Command("admin"))
async def admin(message: Message):

    if message.from_user.id != ADMIN_ID:

        await message.answer(
            "⛔ У тебя нет доступа к админ-панели."
        )

        return

    await message.answer(
        "👑 <b>Панель администратора</b>",
        reply_markup=admin_menu()
    )


# =========================
# КАТАЛОГ
# =========================

@dp.callback_query(F.data == "catalog")
async def catalog(callback: CallbackQuery):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT id, title
            FROM anime
            ORDER BY title
            """
        )

        anime_list = await cursor.fetchall()

    if not anime_list:

        await callback.message.edit_text(
            "📚 <b>Каталог пока пуст.</b>"
        )

        await callback.answer()

        return

    builder = InlineKeyboardBuilder()

    for anime_id, title in anime_list:

        builder.button(
            text=f"🎬 {title}",
            callback_data=f"anime:{anime_id}"
        )

    builder.button(
        text="⬅️ Назад",
        callback_data="home"
    )

    builder.adjust(1)

    await callback.message.edit_text(
        "📚 <b>Каталог аниме:</b>",
        reply_markup=builder.as_markup()
    )

    await callback.answer()


# =========================
# ВЫБОР АНИМЕ
# =========================

@dp.callback_query(F.data.startswith("anime:"))
async def select_anime(callback: CallbackQuery):

    anime_id = int(
        callback.data.split(":")[1]
    )

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT title
            FROM anime
            WHERE id=?
            """,
            (anime_id,)
        )

        anime = await cursor.fetchone()

        cursor = await db.execute(
            """
            SELECT id, season_number
            FROM seasons
            WHERE anime_id=?
            ORDER BY season_number
            """,
            (anime_id,)
        )

        seasons = await cursor.fetchall()

    if not anime:

        await callback.answer(
            "Аниме не найдено."
        )

        return

    builder = InlineKeyboardBuilder()

    for season_id, season_number in seasons:

        builder.button(
            text=f"📺 Сезон {season_number}",
            callback_data=f"season:{season_id}"
        )

    builder.button(
        text="⬅️ Каталог",
        callback_data="catalog"
    )

    builder.adjust(1)

    await callback.message.edit_text(
        f"🎬 <b>{anime[0]}</b>\n\n"
        f"Выбери сезон:",
        reply_markup=builder.as_markup()
    )

    await callback.answer()


# =========================
# ВЫБОР СЕЗОНА
# =========================

@dp.callback_query(F.data.startswith("season:"))
async def select_season(callback: CallbackQuery):

    season_id = int(
        callback.data.split(":")[1]
    )

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT episode_number
            FROM episodes
            WHERE season_id=?
            ORDER BY episode_number
            """,
            (season_id,)
        )

        episodes = await cursor.fetchall()

    if not episodes:

        await callback.answer(
            "В этом сезоне пока нет серий."
        )

        return

    builder = InlineKeyboardBuilder()

    for episode_number, in episodes:

        builder.button(
            text=f"▶️ {episode_number}",
            callback_data=(
                f"episode:{season_id}:{episode_number}"
            )
        )

    builder.button(
        text="⬅️ Назад",
        callback_data="catalog"
    )

    builder.adjust(4)

    await callback.message.edit_text(
        "▶️ <b>Выбери серию:</b>",
        reply_markup=builder.as_markup()
    )

    await callback.answer()


# =========================
# ОТПРАВКА ВИДЕО
# =========================

@dp.callback_query(F.data.startswith("episode:"))
async def send_episode(callback: CallbackQuery):

    parts = callback.data.split(":")

    season_id = int(parts[1])
    episode_number = int(parts[2])

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT file_id
            FROM episodes
            WHERE season_id=?
            AND episode_number=?
            """,
            (
                season_id,
                episode_number
            )
        )

        episode = await cursor.fetchone()

    if not episode:

        await callback.answer(
            "Серия не найдена."
        )

        return

    await callback.message.answer_video(
        video=episode[0],
        caption=f"🎬 Серия {episode_number}"
    )

    await callback.answer()


# =========================
# ГЛАВНОЕ МЕНЮ
# =========================

@dp.callback_query(F.data == "home")
async def home(callback: CallbackQuery):

    await callback.message.edit_text(
        "🎌 <b>Главное меню</b>",
        reply_markup=main_menu()
    )

    await callback.answer()


# =========================
# ДОБАВЛЕНИЕ АНИМЕ
# =========================

@dp.callback_query(F.data == "add_anime")
async def add_anime_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "⛔ Нет доступа."
        )

        return

    await state.set_state(
        AddAnimeState.title
    )

    await callback.message.answer(
        "🎬 Напиши название аниме:"
    )

    await callback.answer()


@dp.message(AddAnimeState.title)
async def add_anime_finish(
    message: Message,
    state: FSMContext
):

    if message.from_user.id != ADMIN_ID:
        return

    title = message.text.strip()

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            INSERT INTO anime(title)
            VALUES(?)
            """,
            (title,)
        )

        await db.commit()

    await state.clear()

    await message.answer(
        f"✅ Аниме <b>{title}</b> добавлено!"
    )


# =========================
# ДОБАВЛЕНИЕ СЕРИИ
# =========================

@dp.callback_query(F.data == "add_episode")
async def add_episode_start(
    callback: CallbackQuery,
    state: FSMContext
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "⛔ Нет доступа."
        )

        return

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT id, title
            FROM anime
            ORDER BY title
            """
        )

        anime_list = await cursor.fetchall()

    if not anime_list:

        await callback.message.answer(
            "❌ Сначала добавь аниме."
        )

        await callback.answer()

        return

    builder = InlineKeyboardBuilder()

    for anime_id, title in anime_list:

        builder.button(
            text=title,
            callback_data=f"addanime:{anime_id}"
        )

    builder.adjust(1)

    await state.set_state(
        AddEpisodeState.anime_id
    )

    await callback.message.answer(
        "🎬 Выбери аниме:",
        reply_markup=builder.as_markup()
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("addanime:")
)
async def choose_anime(
    callback: CallbackQuery,
    state: FSMContext
):

    anime_id = int(
        callback.data.split(":")[1]
    )

    await state.update_data(
        anime_id=anime_id
    )

    await state.set_state(
        AddEpisodeState.season
    )

    await callback.message.answer(
        "📺 Напиши номер сезона.\n\n"
        "Например: <b>1</b>"
    )

    await callback.answer()


@dp.message(AddEpisodeState.season)
async def episode_season(
    message: Message,
    state: FSMContext
):

    if not message.text.isdigit():

        await message.answer(
            "❌ Напиши номер сезона цифрой."
        )

        return

    await state.update_data(
        season=int(message.text)
    )

    await state.set_state(
        AddEpisodeState.episode
    )

    await message.answer(
        "▶️ Напиши номер серии.\n\n"
        "Например: <b>1</b>"
    )


@dp.message(AddEpisodeState.episode)
async def episode_number(
    message: Message,
    state: FSMContext
):

    if not message.text.isdigit():

        await message.answer(
            "❌ Напиши номер серии цифрой."
        )

        return

    await state.update_data(
        episode=int(message.text)
    )

    await state.set_state(
        AddEpisodeState.video
    )

    await message.answer(
        "🎥 Теперь отправь видео этой серии."
    )


@dp.message(
    AddEpisodeState.video,
    F.video
)
async def save_episode(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()

    anime_id = data["anime_id"]
    season_number = data["season"]
    episode_number = data["episode"]

    file_id = message.video.file_id

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT id
            FROM seasons
            WHERE anime_id=?
            AND season_number=?
            """,
            (
                anime_id,
                season_number
            )
        )

        season = await cursor.fetchone()

        if season:

            season_id = season[0]

        else:

            cursor = await db.execute(
                """
                INSERT INTO seasons
                (
                    anime_id,
                    season_number
                )
                VALUES (?, ?)
                """,
                (
                    anime_id,
                    season_number
                )
            )

            season_id = cursor.lastrowid

        await db.execute(
            """
            INSERT OR REPLACE INTO episodes
            (
                season_id,
                episode_number,
                file_id
            )
            VALUES (?, ?, ?)
            """,
            (
                season_id,
                episode_number,
                file_id
            )
        )

        await db.commit()

    await state.clear()

    await message.answer(
        f"✅ <b>Серия {episode_number}</b> добавлена!"
    )


# =========================
# УДАЛЕНИЕ АНИМЕ
# =========================

@dp.callback_query(F.data == "delete_anime")
async def delete_anime_start(
    callback: CallbackQuery
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "⛔ Нет доступа."
        )

        return

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            """
            SELECT id, title
            FROM anime
            ORDER BY title
            """
        )

        anime_list = await cursor.fetchall()

    if not anime_list:

        await callback.message.answer(
            "📚 Каталог пуст."
        )

        await callback.answer()

        return

    builder = InlineKeyboardBuilder()

    for anime_id, title in anime_list:

        builder.button(
            text=f"🗑 {title}",
            callback_data=f"delete:{anime_id}"
        )

    builder.adjust(1)

    await callback.message.answer(
        "🗑 Выбери аниме для удаления:",
        reply_markup=builder.as_markup()
    )

    await callback.answer()


@dp.callback_query(
    F.data.startswith("delete:")
)
async def delete_anime(
    callback: CallbackQuery
):

    if callback.from_user.id != ADMIN_ID:

        await callback.answer(
            "⛔ Нет доступа."
        )

        return

    anime_id = int(
        callback.data.split(":")[1]
    )

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            """
            DELETE FROM episodes
            WHERE season_id IN (
                SELECT id
                FROM seasons
                WHERE anime_id=?
            )
            """,
            (anime_id,)
        )

        await db.execute(
            """
            DELETE FROM seasons
            WHERE anime_id=?
            """,
            (anime_id,)
        )

        await db.execute(
            """
            DELETE FROM anime
            WHERE id=?
            """,
            (anime_id,)
        )

        await db.commit()

    await callback.message.answer(
        "✅ Аниме и все его серии удалены."
    )

    await callback.answer()


# =========================
# ЗАПУСК
# =========================

async def main():

    if not BOT_TOKEN:

        print(
            "❌ BOT_TOKEN не найден!"
        )

        return

    await init_db()

    print(
        "🤖 Бот запущен!"
    )

    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
