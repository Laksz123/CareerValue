from aiogram import Router, types, F
from typing import Optional, Tuple
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config import ADMIN_IDS
from utils.admin_states import AdminStates, EditSettingsStates, EditDelaysStates, EditTextsStates
from utils.db_api import (
    get_stats,
    get_all_users,
    get_setting,
    set_setting,
    add_vacancy_post,
    get_all_vacancy_posts,
    delete_vacancy_post,
)

router = Router()

def is_admin(user_id: int):
    return user_id in ADMIN_IDS

def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📊 Статистика"))
    builder.row(types.KeyboardButton(text="📄 Вакансии"), types.KeyboardButton(text="📢 Рассылка"))
    builder.row(types.KeyboardButton(text="🔗 Ссылки"), types.KeyboardButton(text="⏱ Задержки"))
    builder.row(types.KeyboardButton(text="📝 Тексты"))
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
    await message.answer(
        f"🔗 Текущие ссылки:\n\n"
        f"📞 Кнопка «Связаться» (экран «Как выйти на X ₽»): {contact_link}",
        reply_markup=builder.as_markup()
    )

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

@router.message(F.text == "⏱ Задержки")
async def admin_delays(message: types.Message):
    if not is_admin(message.from_user.id): return
    loading_min = await get_setting("delay_loading_min", "0.7")
    loading_max = await get_setting("delay_loading_max", "1.2")
    vacancy_min = await get_setting("delay_vacancy_min", "0.5")
    vacancy_max = await get_setting("delay_vacancy_max", "1.5")
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✏️ Задержки загрузки (min-max сек)", callback_data="admin_edit_loading_delays"))
    builder.row(types.InlineKeyboardButton(text="✏️ Пауза перед вакансиями (min-max сек)", callback_data="admin_edit_vacancy_delays"))
    await message.answer(
        f"⏱ Текущие задержки (секунды):\n\n"
        f"Загрузка (анимация): {loading_min} - {loading_max}\n"
        f"Перед показом вакансий: {vacancy_min} - {vacancy_max}",
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "admin_edit_loading_delays")
async def start_edit_loading_delays(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите min и max для загрузки через пробел (например: 0.5 1.5):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(EditDelaysStates.waiting_for_loading_delays)
    await callback.answer()

@router.callback_query(F.data == "admin_edit_vacancy_delays")
async def start_edit_vacancy_delays(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введите min и max для паузы перед вакансиями через пробел (например: 0.5 1.5):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(EditDelaysStates.waiting_for_vacancy_delays)
    await callback.answer()

def _parse_delays(text: str) -> Optional[Tuple[float, float]]:
    parts = text.strip().split()
    if len(parts) != 2:
        return None
    try:
        a, b = float(parts[0]), float(parts[1])
        if a < 0 or b < 0:
            return None
        return (min(a, b), max(a, b))
    except ValueError:
        return None

@router.message(EditDelaysStates.waiting_for_loading_delays)
async def process_loading_delays(message: types.Message, state: FSMContext):
    parsed = _parse_delays(message.text)
    if not parsed:
        await message.answer("❌ Введите два числа через пробел (например: 0.5 1.5):")
        return
    await set_setting("delay_loading_min", str(parsed[0]))
    await set_setting("delay_loading_max", str(parsed[1]))
    await message.answer(f"✅ Задержки загрузки обновлены: {parsed[0]} - {parsed[1]} сек", reply_markup=get_admin_keyboard())
    await state.clear()

@router.message(EditDelaysStates.waiting_for_vacancy_delays)
async def process_vacancy_delays(message: types.Message, state: FSMContext):
    parsed = _parse_delays(message.text)
    if not parsed:
        await message.answer("❌ Введите два числа через пробел (например: 0.5 1.5):")
        return
    await set_setting("delay_vacancy_min", str(parsed[0]))
    await set_setting("delay_vacancy_max", str(parsed[1]))
    await message.answer(f"✅ Пауза перед вакансиями обновлена: {parsed[0]} - {parsed[1]} сек", reply_markup=get_admin_keyboard())
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
