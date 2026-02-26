from aiogram import Router, types, F
import secrets
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config import ADMIN_IDS
from utils.admin_states import AdminStates, EditSettingsStates, EditDelaysStates, EditTextsStates, ReferralLinkStates
from utils.db_api import (
    get_stats,
    get_all_users,
    get_setting,
    set_setting,
    add_vacancy_post,
    get_all_vacancy_posts,
    delete_vacancy_post,
    create_referral_link,
    get_all_referral_links,
    delete_referral_link,
)

router = Router()

def is_admin(user_id: int):
    return user_id in ADMIN_IDS

def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📊 Статистика"))
    builder.row(types.KeyboardButton(text="📄 Вакансии"), types.KeyboardButton(text="📢 Рассылка"))
    builder.row(types.KeyboardButton(text="🔗 Ссылки"), types.KeyboardButton(text="📊 Реферальные ссылки"))
    builder.row(types.KeyboardButton(text="⏱ Задержки"), types.KeyboardButton(text="📝 Тексты"))
    builder.row(types.KeyboardButton(text="❌ Выйти из админки"))
    return builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="❌ Отмена"))
    return builder.as_markup(resize_keyboard=True)

@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🛠 Панель администратора открыта", reply_markup=get_admin_keyboard())

@router.message(F.text == "❌ Выйти из админки")
async def admin_exit(message: types.Message):
    await message.answer("Вы вышли из админки", reply_markup=types.ReplyKeyboardRemove())

@router.message(F.text == "❌ Отмена")
async def admin_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено", reply_markup=get_admin_keyboard())

@router.message(F.text == "📊 Статистика")
async def admin_stats_msg(message: types.Message):
    if not is_admin(message.from_user.id): return
    stats = await get_stats()
    await message.answer(
        "📊 Статистика бота:\n\n"
        f"👥 Всего пользователей: {stats['total']}\n"
        f"✅ Прошли тест: {stats['completed']}\n"
    )

@router.message(F.text == "📄 Вакансии")
async def admin_vacancies_msg(message: types.Message):
    if not is_admin(message.from_user.id): return
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📋 Список всех", callback_data="admin_vac_list"))
    builder.row(types.InlineKeyboardButton(text="➕ Добавить новую", callback_data="admin_add_vacancy"))
    await message.answer("Управление вакансиями:", reply_markup=builder.as_markup())

@router.callback_query(F.data == "admin_vac_list")
async def admin_vac_list(callback: types.CallbackQuery):
    posts = await get_all_vacancy_posts()
    if not posts:
        await callback.message.answer("Постов пока нет.")
        await callback.answer()
        return

    for p in posts:
        preview = (p.text[:50] + "…") if p.text and len(p.text) > 50 else (p.text or "—")
        text = f"ID: {p.id}\n📄 {preview}"
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="❌ Удалить", callback_data=f"admin_del_post_{p.id}"))
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_del_post_"))
async def admin_del_post(callback: types.CallbackQuery):
    post_id = int(callback.data.split("_")[-1])
    if await delete_vacancy_post(post_id):
        await callback.message.delete()
        await callback.message.answer(f"✅ Пост ID {post_id} удалён")
    else:
        await callback.message.answer("Ошибка удаления")
    await callback.answer()


# --- Vacancy Post Addition Flow ---

@router.callback_query(F.data == "admin_add_vacancy")
async def start_add_vacancy(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Отправьте пост вакансии (текст, фото, ссылки, цитаты — всё сохранится как есть):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_vacancy_post)
    await callback.answer()


@router.message(AdminStates.waiting_for_vacancy_post, F.text)
@router.message(AdminStates.waiting_for_vacancy_post, F.photo)
async def process_vacancy_post(message: types.Message, state: FSMContext):
    import json
    from aiogram.types import MessageEntity

    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_admin_keyboard())
        return

    content_type = "photo" if message.photo else "text"
    text = message.caption or message.text or ""
    if not text:
        await message.answer("Отправьте пост с текстом или подписью к фото.")
        return

    entities = message.entities or message.caption_entities or []
    entities_json = json.dumps([e.model_dump() for e in entities]) if entities else None

    photo_file_id = message.photo[-1].file_id if message.photo else None

    await add_vacancy_post(
        content_type=content_type,
        text=text,
        entities_json=entities_json,
        photo_file_id=photo_file_id,
    )

    await message.answer("Сохранено. Ниже пост, как бот будет его отправлять:", reply_markup=get_admin_keyboard())
    await state.clear()

    # Preview: send copy of the post
    try:
        await message.send_copy(chat_id=message.chat.id)
    except (TypeError, Exception):
        entities_list = [MessageEntity.model_validate(e) for e in json.loads(entities_json or "[]")]
        if content_type == "photo":
            await message.bot.send_photo(
                chat_id=message.chat.id,
                photo=photo_file_id,
                caption=text,
                caption_entities=entities_list,
            )
        else:
            await message.bot.send_message(
                chat_id=message.chat.id,
                text=text,
                entities=entities_list,
            )

# --- Broadcast Flow ---

@router.message(F.text == "📢 Рассылка")
async def start_broadcast(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    await message.answer("Введите текст для рассылки всем пользователям:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_broadcast_text)

@router.message(AdminStates.waiting_for_broadcast_text)
async def process_broadcast(message: types.Message, state: FSMContext):
    user_ids = await get_all_users()
    count = 0
    for uid in user_ids:
        try:
            await message.bot.send_message(uid, message.text)
            count += 1
        except Exception: pass
    await message.answer(
        f"✅ Рассылка завершена! Получили: {count} пользователей.",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()

# --- Settings / Links Management ---

@router.message(F.text == "🔗 Ссылки")
async def admin_links(message: types.Message):
    if not is_admin(message.from_user.id): return
    contact_link = await get_setting("contact_link", "https://t.me")
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✏️ Изменить ссылку контакта", callback_data="admin_edit_contact_link"))
    builder.row(types.InlineKeyboardButton(text="📊 Реферальные ссылки", callback_data="admin_referral_links"))
    await message.answer(
        f"🔗 Текущие ссылки:\n\n"
        f"📞 Кнопка «Связаться» (экран «Как выйти на X ₽»): {contact_link}",
        reply_markup=builder.as_markup()
    )


# --- Referral Links ---

def _format_date(dt) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M")

async def _show_referral_links(message_or_callback, is_callback: bool = False):
    """Show referral links list. message_or_callback has .message.answer and .bot for callback, or .answer and .bot for message."""
    target = message_or_callback.message if is_callback else message_or_callback
    bot = message_or_callback.bot if is_callback else message_or_callback.bot
    links = await get_all_referral_links()
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="➕ Создать ссылку", callback_data="admin_create_referral_link"))
    if not links:
        await target.answer(
            "📊 Реферальные ссылки\n\nПока нет ни одной ссылки. Создайте первую!",
            reply_markup=builder.as_markup()
        )
    else:
        try:
            bot_info = await bot.get_me()
            bot_username = bot_info.username or "bot"
        except Exception:
            bot_username = "bot"
        base_url = f"https://t.me/{bot_username}"
        await target.answer("📊 Реферальные ссылки:", reply_markup=builder.as_markup())
        for link in links:
            full_url = f"{base_url}?start=ref_{link.slug}"
            del_builder = InlineKeyboardBuilder()
            del_builder.row(types.InlineKeyboardButton(text="❌ Удалить", callback_data=f"admin_del_ref_{link.id}"))
            await target.answer(
                f"📌 {link.name}\n"
                f"🔗 {full_url}\n"
                f"👆 Переходов: {link.clicks} | 📅 Создана: {_format_date(link.created_at)}",
                reply_markup=del_builder.as_markup()
            )


@router.message(F.text == "📊 Реферальные ссылки")
async def admin_referral_links_msg(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await _show_referral_links(message, is_callback=False)


@router.callback_query(F.data == "admin_referral_links")
async def admin_referral_links_list(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    await _show_referral_links(callback, is_callback=True)
    await callback.answer()


@router.callback_query(F.data == "admin_create_referral_link")
async def start_create_referral_link(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите название для реферальной ссылки (например: «Кампания ВК» или «Реклама в Telegram»):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ReferralLinkStates.waiting_for_link_name)
    await callback.answer()


@router.message(ReferralLinkStates.waiting_for_link_name)
async def process_referral_link_name(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_admin_keyboard())
        return
    name = message.text.strip()
    if not name:
        await message.answer("Введите непустое название:")
        return
    slug = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].lower()
    link = await create_referral_link(name=name, slug=slug)
    if not link:
        await message.answer("Ошибка: не удалось создать ссылку (возможно, slug занят). Попробуйте снова.")
        return
    try:
        bot_info = await message.bot.get_me()
        bot_username = bot_info.username or "bot"
    except Exception:
        bot_username = "bot"
    full_url = f"https://t.me/{bot_username}?start=ref_{link.slug}"
    await message.answer(
        f"✅ Реферальная ссылка создана!\n\n"
        f"📌 Название: {link.name}\n"
        f"🔗 Ссылка: {full_url}\n"
        f"📅 Создана: {_format_date(link.created_at)}\n\n"
        f"Каждый переход по этой ссылке будет учитываться в статистике.",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()


@router.callback_query(F.data.startswith("admin_del_ref_"))
async def admin_delete_referral_link(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer()
        return
    link_id = int(callback.data.split("_")[-1])
    if await delete_referral_link(link_id):
        await callback.message.delete()
        await callback.message.answer("✅ Реферальная ссылка удалена")
    else:
        await callback.message.answer("Ошибка удаления")
    await callback.answer()

@router.callback_query(F.data == "admin_edit_contact_link")
async def start_edit_contact_link(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите новую ссылку для кнопки контакта (например https://t.me/username):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(EditSettingsStates.waiting_for_contact_link)
    await callback.answer()

@router.message(EditSettingsStates.waiting_for_contact_link)
async def process_contact_link(message: types.Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith(("http://", "https://")):
        if "." in url or url.startswith("@"):
            url = "https://" + url.lstrip("@")
        else:
            await message.answer("❌ Неверный формат ссылки. Попробуйте ещё раз:")
            return
    await set_setting("contact_link", url)
    await message.answer(f"✅ Ссылка контакта обновлена: {url}", reply_markup=get_admin_keyboard())
    await state.clear()


# --- Delays Management ---

VACANCY_DELAY_KEYS = [
    ("delay_vacancy_1", "1-я вакансия"),
    ("delay_vacancy_2", "2-я вакансия"),
    ("delay_vacancy_3", "3-я вакансия"),
    ("delay_vacancy_4", "4-я вакансия"),
    ("delay_vacancy_5", "5-я вакансия"),
]
VACANCY_DELAY_DEFAULTS = ["0", "10", "20", "50", "60"]


def _format_delay_sec(sec: float) -> str:
    """Форматирует секунды: 90 -> '1 мин 30 сек', 60 -> '1 мин', 10 -> '10 сек'."""
    s = int(sec)
    if s >= 60:
        m, r = divmod(s, 60)
        return f"{m} мин {r} сек" if r else f"{m} мин"
    return f"{s} сек"


@router.message(F.text == "⏱ Задержки")
async def admin_delays(message: types.Message):
    if not is_admin(message.from_user.id): return

    delay_loading_duration = await get_setting("delay_loading_duration", "3")
    try:
        loading_sec = float(delay_loading_duration)
    except ValueError:
        loading_sec = 3

    vacancy_lines = []
    for (key, label), default in zip(VACANCY_DELAY_KEYS, VACANCY_DELAY_DEFAULTS):
        val = await get_setting(key, default)
        try:
            sec = float(val)
            vacancy_lines.append(f"🔹 {label} — {_format_delay_sec(sec)}")
        except ValueError:
            vacancy_lines.append(f"🔹 {label} — {val}")

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text=f"GIF поиска — {_format_delay_sec(loading_sec)}",
        callback_data="admin_edit_delay_loading_duration"
    ))
    for i, (key, label) in enumerate(VACANCY_DELAY_KEYS):
        val = await get_setting(key, VACANCY_DELAY_DEFAULTS[i])
        try:
            v_sec = float(val)
        except ValueError:
            v_sec = 0
        builder.row(types.InlineKeyboardButton(
            text=f"🔹 {label} — {_format_delay_sec(v_sec)}",
            callback_data=f"admin_edit_vacancy_delay_{key}"
        ))
    await message.answer(
        "⏱️ НАСТРОЙКИ ЗАДЕРЖЕК\n\n"
        f"🖼  GIF поиска: {loading_sec:.1f} сек\n\n"
        "⏳ Интервалы между вакансиями:\n" + "\n".join(vacancy_lines),
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "admin_edit_delay_loading_duration")
async def start_edit_delay_loading_duration(callback: types.CallbackQuery, state: FSMContext):
    current = await get_setting("delay_loading_duration", "3")
    await callback.message.answer(
        f"Длительность анализа (сколько идёт гифка)\n\n"
        f"Текущее значение: {current} сек\n\n"
        f"Введите длительность в секундах (например: 3 или 5):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(EditDelaysStates.waiting_for_delay_loading_duration)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_vacancy_delay_"))
async def start_edit_vacancy_delay(callback: types.CallbackQuery, state: FSMContext):
    key = callback.data.replace("admin_edit_vacancy_delay_", "")
    label = next((lbl for k, lbl in VACANCY_DELAY_KEYS if k == key), key)
    default = next((d for (k, _), d in zip(VACANCY_DELAY_KEYS, VACANCY_DELAY_DEFAULTS) if k == key), "0")
    current = await get_setting(key, default)
    await state.update_data(edit_vacancy_delay_key=key, edit_vacancy_delay_label=label)
    await callback.message.answer(
        f"Задержка перед «{label}»\n\n"
        f"Текущее значение: {current} сек\n\n"
        f"Введите задержку в секундах (например: 10 или 1.5):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(EditDelaysStates.waiting_for_vacancy_delay)
    await callback.answer()


@router.message(EditDelaysStates.waiting_for_delay_loading_duration)
async def process_delay_loading_duration(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_admin_keyboard())
        return
    try:
        sec = float(message.text.strip().replace(",", "."))
        if sec < 0:
            raise ValueError("Отрицательное значение")
    except ValueError:
        await message.answer("❌ Введите число (секунды), например: 3 или 5")
        return
    await set_setting("delay_loading_duration", str(sec))
    await message.answer(
        f"✅ Длительность анализа обновлена: {_format_delay_sec(sec)}",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()


@router.message(EditDelaysStates.waiting_for_vacancy_delay)
async def process_vacancy_delay(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_admin_keyboard())
        return
    try:
        sec = float(message.text.strip().replace(",", "."))
        if sec < 0:
            raise ValueError("Отрицательное значение")
    except ValueError:
        await message.answer("❌ Введите число (секунды), например: 10 или 1.5")
        return
    data = await state.get_data()
    key = data.get("edit_vacancy_delay_key")
    label = data.get("edit_vacancy_delay_label", "вакансия")
    if key:
        await set_setting(key, str(sec))
        await message.answer(
            f"✅ Задержка для «{label}» обновлена: {_format_delay_sec(sec)}",
            reply_markup=get_admin_keyboard()
        )
    await state.clear()


# --- Texts Management ---

TEXT_KEYS = {
    "text_welcome": "Приветствие (START, {name})",
    "text_vacancy_intro": "Вступление к вакансиям ({count})",
    "text_no_vacancies": "Текст при отсутствии вакансий",
    "text_how_to_increase": "Советы «Как выйти на X ₽»",
    "text_loading_1": "Загрузка шаг 1",
    "text_loading_2": "Загрузка шаг 2",
    "text_result": "Шаблон результата ({market_value}, {potential_value}, {career_index})",
}

@router.message(F.text == "📝 Тексты")
async def admin_texts(message: types.Message):
    if not is_admin(message.from_user.id): return
    builder = InlineKeyboardBuilder()
    for key, label in TEXT_KEYS.items():
        builder.row(types.InlineKeyboardButton(text=f"✏️ {label}", callback_data=f"admin_edit_text_{key}"))
    await message.answer("Выберите текст для редактирования:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("admin_edit_text_"))
async def start_edit_text(callback: types.CallbackQuery, state: FSMContext):
    key = callback.data.replace("admin_edit_text_", "")
    await state.update_data(edit_text_key=key)
    current = await get_setting(key, "")
    await callback.message.answer(
        f"Текущее значение для «{TEXT_KEYS.get(key, key)}»:\n\n{current[:500]}{'...' if len(current) > 500 else ''}\n\nВведите новый текст (или '-' чтобы оставить):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(EditTextsStates.waiting_for_text_value)
    await callback.answer()

@router.message(EditTextsStates.waiting_for_text_value)
async def process_text_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("edit_text_key")
    if message.text != "-" and key:
        await set_setting(key, message.text)
        await message.answer(f"✅ Текст «{TEXT_KEYS.get(key, key)}» обновлён!", reply_markup=get_admin_keyboard())
    else:
        await message.answer("Изменения отменены.", reply_markup=get_admin_keyboard())
    await state.clear()
