from aiogram import Router, types, F
from typing import Optional, Tuple
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config import ADMIN_IDS
from utils.admin_states import AdminStates, EditVacancyStates, EditSettingsStates, EditDelaysStates, EditTextsStates
from utils.db_api import get_stats, add_vacancy, get_all_vacancies, get_vacancy, delete_vacancy, get_all_users, update_vacancy, get_setting, set_setting

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
    vacs = await get_all_vacancies()
    if not vacs:
        await callback.message.answer("Вакансий пока нет.")
        await callback.answer()
        return

    for v in vacs:
        link_preview = (v.link[:40] + "…") if v.link and len(v.link) > 40 else (v.link or "—")
        text = f"ID: {v.id}\n🔹 {v.title} в {v.company}\n📍 {v.city}\n🔗 Ссылка: {link_preview}"
        builder = InlineKeyboardBuilder()
        builder.row(
            types.InlineKeyboardButton(text="✏️ Изменить", callback_data=f"admin_edit_vac_{v.id}"),
            types.InlineKeyboardButton(text="❌ Удалить", callback_data=f"admin_del_vac_{v.id}")
        )
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("admin_del_vac_"))
async def admin_del_vac(callback: types.CallbackQuery):
    vac_id = int(callback.data.split("_")[-1])
    if await delete_vacancy(vac_id):
        await callback.message.delete()
        await callback.message.answer(f"✅ Вакансия ID {vac_id} удалена")
    else:
        await callback.message.answer("Ошибка удаления")
    await callback.answer()

# --- Vacancy Editing Flow (inline field selection) ---

SPHERES = [
    ("💻 IT", "IT"),
    ("💬 Продажи", "Продажи"),
    ("📦 Склад", "Склад"),
    ("🚚 Логистика", "Логистика"),
]

def fix_url(url: str) -> str:
    url = url.strip()
    if not url or url == "-": return url
    if not url.startswith(("http://", "https://")):
        if "." in url: return "https://" + url
    return url


def _vacancy_edit_card(vac) -> str:
    """Build vacancy card text for edit view."""
    link_preview = (vac.link[:50] + "…") if vac.link and len(vac.link) > 50 else (vac.link or "—")
    return (
        f"📝 Вакансия ID {vac.id}\n\n"
        f"🔹 Название: {vac.title}\n"
        f"🏢 Компания: {vac.company}\n"
        f"📍 Город: {vac.city}\n"
        f"📂 Сфера: {vac.sphere}\n"
        f"💰 Зарплата: {vac.salary_min or '—'} - {vac.salary_max or '—'}\n"
        f"🔗 Ссылка: {link_preview}\n"
        f"📄 Описание: {(vac.description or '—')[:80]}{'…' if (vac.description or '') and len(vac.description or '') > 80 else ''}"
    )


def _vacancy_edit_buttons(vac_id: int) -> InlineKeyboardBuilder:
    """Build inline keyboard for vacancy edit fields."""
    b = InlineKeyboardBuilder()
    b.row(
        types.InlineKeyboardButton(text="✏️ Название", callback_data=f"admin_vac_edit_{vac_id}_title"),
        types.InlineKeyboardButton(text="✏️ Компания", callback_data=f"admin_vac_edit_{vac_id}_company"),
    )
    b.row(
        types.InlineKeyboardButton(text="✏️ Город", callback_data=f"admin_vac_edit_{vac_id}_city"),
        types.InlineKeyboardButton(text="✏️ Сфера", callback_data=f"admin_vac_edit_{vac_id}_sphere"),
    )
    b.row(
        types.InlineKeyboardButton(text="✏️ Зарплата", callback_data=f"admin_vac_edit_{vac_id}_salary"),
        types.InlineKeyboardButton(text="✏️ Ссылка", callback_data=f"admin_vac_edit_{vac_id}_link"),
    )
    b.row(types.InlineKeyboardButton(text="✏️ Описание", callback_data=f"admin_vac_edit_{vac_id}_desc"))
    b.row(
        types.InlineKeyboardButton(text="✅ Готово", callback_data=f"admin_vac_done_{vac_id}"),
        types.InlineKeyboardButton(text="❌ Удалить", callback_data=f"admin_del_vac_{vac_id}"),
    )
    return b


@router.callback_query(F.data.startswith("admin_edit_vac_"))
async def start_edit_vacancy(callback: types.CallbackQuery, state: FSMContext):
    vac_id = int(callback.data.split("_")[-1])
    vac = await get_vacancy(vac_id)
    if not vac:
        await callback.answer("Вакансия не найдена")
        return
    text = _vacancy_edit_card(vac)
    await callback.message.edit_text(text, reply_markup=_vacancy_edit_buttons(vac_id).as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_vac_edit_"))
async def vac_edit_field(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    vac_id = int(parts[3])
    field = parts[4]
    vac = await get_vacancy(vac_id)
    if not vac:
        await callback.answer("Вакансия не найдена")
        return

    if field == "sphere":
        b = InlineKeyboardBuilder()
        for i, (label, db_val) in enumerate(SPHERES):
            b.row(types.InlineKeyboardButton(text=label, callback_data=f"admin_vac_sphere_{vac_id}_{i}"))
        b.row(types.InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_edit_vac_{vac_id}"))
        await callback.message.edit_text(
            f"📂 Выберите сферу для вакансии «{vac.title}»:",
            reply_markup=b.as_markup()
        )
        await callback.answer()
        return

    if field == "salary":
        await state.update_data(edit_vac_id=vac_id, edit_field="salary")
        await callback.message.answer(
            f"💰 Введите зарплату (min max через пробел, например: 80000 120000):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(EditVacancyStates.waiting_for_edit_value)
        await callback.answer()
        return

    prompts = {
        "title": ("🔹 Введите новое название:", "title"),
        "company": ("🏢 Введите название компании:", "company"),
        "city": ("📍 Введите город:", "city"),
        "link": ("🔗 Введите ссылку:", "link"),
        "desc": ("📄 Введите описание:", "description"),
    }
    if field not in prompts:
        await callback.answer()
        return
    prompt, db_field = prompts[field]
    await state.update_data(edit_vac_id=vac_id, edit_field=db_field)
    await callback.message.answer(prompt, reply_markup=get_cancel_keyboard())
    await state.set_state(EditVacancyStates.waiting_for_edit_value)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_vac_sphere_"))
async def vac_set_sphere(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    vac_id = int(parts[3])
    idx = int(parts[4])
    sphere = SPHERES[idx][1] if 0 <= idx < len(SPHERES) else "IT"
    await update_vacancy(vac_id, sphere=sphere)
    vac = await get_vacancy(vac_id)
    text = _vacancy_edit_card(vac)
    await callback.message.edit_text(text, reply_markup=_vacancy_edit_buttons(vac_id).as_markup())
    await callback.answer("✅ Сфера обновлена")


@router.callback_query(F.data.startswith("admin_vac_done_"))
async def vac_edit_done(callback: types.CallbackQuery, state: FSMContext):
    vac_id = int(callback.data.split("_")[-1])
    vac = await get_vacancy(vac_id)
    text = _vacancy_edit_card(vac)
    await callback.message.edit_text(text, reply_markup=_vacancy_edit_buttons(vac_id).as_markup())
    await callback.message.answer("✅ Редактирование завершено", reply_markup=get_admin_keyboard())
    await state.clear()
    await callback.answer()


@router.message(EditVacancyStates.waiting_for_edit_value)
async def vac_edit_value_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    vac_id = data.get("edit_vac_id")
    field = data.get("edit_field")
    if not vac_id or not field:
        await state.clear()
        await message.answer("Сессия истекла.", reply_markup=get_admin_keyboard())
        return

    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=get_admin_keyboard())
        return

    if field == "salary":
        parts = message.text.strip().split()
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            await message.answer("❌ Введите два числа через пробел (например: 80000 120000):")
            return
        await update_vacancy(vac_id, salary_min=int(parts[0]), salary_max=int(parts[1]))
    elif field == "link":
        await update_vacancy(vac_id, link=fix_url(message.text))
    else:
        await update_vacancy(vac_id, **{field: message.text})

    vac = await get_vacancy(vac_id)
    await state.clear()
    await message.answer(
        "✅ Обновлено!\n\n" + _vacancy_edit_card(vac),
        reply_markup=_vacancy_edit_buttons(vac_id).as_markup()
    )

# --- Vacancy Addition Flow ---

@router.callback_query(F.data == "admin_add_vacancy")
async def start_add_vacancy(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название вакансии:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_vacancy_title)
    await callback.answer()

@router.message(AdminStates.waiting_for_vacancy_title)
async def process_vac_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите название компании:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_vacancy_company)

@router.message(AdminStates.waiting_for_vacancy_company)
async def process_vac_company(message: types.Message, state: FSMContext):
    await state.update_data(company=message.text)
    await message.answer("Введите город:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_vacancy_city)

@router.message(AdminStates.waiting_for_vacancy_city)
async def process_vac_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    b = InlineKeyboardBuilder()
    for i, (label, _) in enumerate(SPHERES):
        b.row(types.InlineKeyboardButton(text=label, callback_data=f"admin_add_sphere_{i}"))
    b.row(types.InlineKeyboardButton(text="❌ Отмена", callback_data="admin_add_cancel"))
    await message.answer("📂 Выберите сферу:", reply_markup=b.as_markup())
    await state.set_state(AdminStates.waiting_for_vacancy_sphere)

@router.callback_query(F.data == "admin_add_cancel")
async def process_add_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Добавление вакансии отменено.")
    await callback.message.answer("Действие отменено", reply_markup=get_admin_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("admin_add_sphere_"))
async def process_add_sphere(callback: types.CallbackQuery, state: FSMContext):
    if "waiting_for_vacancy_sphere" not in (await state.get_state() or ""):
        await callback.answer()
        return
    idx = int(callback.data.split("_")[-1])
    sphere = SPHERES[idx][1] if 0 <= idx < len(SPHERES) else "IT"
    await state.update_data(sphere=sphere)
    await callback.message.edit_text(f"✅ Сфера: {sphere}")
    await callback.message.answer("Введите минимальную зарплату (число):", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_vacancy_salary_min)
    await callback.answer()

@router.message(AdminStates.waiting_for_vacancy_salary_min)
async def process_vac_salary_min(message: types.Message, state: FSMContext):
    await state.update_data(salary_min=int(message.text) if message.text.isdigit() else 0)
    await message.answer("Введите максимальную зарплату (число):", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_vacancy_salary_max)

@router.message(AdminStates.waiting_for_vacancy_salary_max)
async def process_vac_salary_max(message: types.Message, state: FSMContext):
    await state.update_data(salary_max=int(message.text) if message.text.isdigit() else 0)
    await message.answer("Введите ссылку на вакансию:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_vacancy_link)

@router.message(AdminStates.waiting_for_vacancy_link)
async def process_vac_link(message: types.Message, state: FSMContext):
    await state.update_data(link=fix_url(message.text))
    await message.answer("Введите описание:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_vacancy_desc)

@router.message(AdminStates.waiting_for_vacancy_desc)
async def process_vac_desc(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await add_vacancy(
        title=data['title'], company=data['company'], city=data['city'],
        sphere=data['sphere'], experience="Любой", description=message.text,
        salary_min=data.get('salary_min', 0), salary_max=data.get('salary_max', 0),
        link=data.get('link', "")
    )
    await message.answer("✅ Вакансия добавлена!", reply_markup=get_admin_keyboard())
    await state.clear()

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
