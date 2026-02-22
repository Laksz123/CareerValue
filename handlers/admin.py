from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from config import ADMIN_IDS
from utils.admin_states import AdminStates, EditVacancyStates
from utils.db_api import get_stats, add_vacancy, get_all_vacancies, delete_vacancy, get_all_users, update_vacancy

router = Router()

def is_admin(user_id: int):
    return user_id in ADMIN_IDS

def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="📊 Статистика"))
    builder.row(types.KeyboardButton(text="📄 Вакансии"), types.KeyboardButton(text="📢 Рассылка"))
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
        text = f"ID: {v.id}\n🔹 {v.title} в {v.company}\n📍 {v.city}"
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

# --- Vacancy Editing Flow ---

@router.callback_query(F.data.startswith("admin_edit_vac_"))
async def start_edit_vacancy(callback: types.CallbackQuery, state: FSMContext):
    vac_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_vac_id=vac_id)
    await callback.message.answer(
        f"📝 Редактирование вакансии ID {vac_id}\nВведите НОВОЕ название (или напишите '-', чтобы оставить прежнее):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(EditVacancyStates.waiting_for_vacancy_title)
    await callback.answer()

@router.message(EditVacancyStates.waiting_for_vacancy_title)
async def edit_vac_title(message: types.Message, state: FSMContext):
    if message.text != "-":
        await state.update_data(title=message.text)
    await message.answer("Введите НОВУЮ компанию (или '-'):")
    await state.set_state(EditVacancyStates.waiting_for_vacancy_company)

@router.message(EditVacancyStates.waiting_for_vacancy_company)
async def edit_vac_company(message: types.Message, state: FSMContext):
    if message.text != "-":
        await state.update_data(company=message.text)
    await message.answer("Введите НОВЫЙ город (или '-'):")
    await state.set_state(EditVacancyStates.waiting_for_vacancy_city)

@router.message(EditVacancyStates.waiting_for_vacancy_city)
async def edit_vac_city(message: types.Message, state: FSMContext):
    if message.text != "-":
        await state.update_data(city=message.text)
    await message.answer("Введите НОВУЮ сферу (или '-'):")
    await state.set_state(EditVacancyStates.waiting_for_vacancy_sphere)

@router.message(EditVacancyStates.waiting_for_vacancy_sphere)
async def edit_vac_sphere(message: types.Message, state: FSMContext):
    if message.text != "-":
        await state.update_data(sphere=message.text)
    await message.answer("Введите НОВУЮ мин. зарплату (или '-'):")
    await state.set_state(EditVacancyStates.waiting_for_vacancy_salary_min)

@router.message(EditVacancyStates.waiting_for_vacancy_salary_min)
async def edit_vac_salary_min(message: types.Message, state: FSMContext):
    if message.text != "-":
        await state.update_data(salary_min=int(message.text) if message.text.isdigit() else 0)
    await message.answer("Введите НОВУЮ макс. зарплату (или '-'):")
    await state.set_state(EditVacancyStates.waiting_for_vacancy_salary_max)

@router.message(EditVacancyStates.waiting_for_vacancy_salary_max)
async def edit_vac_salary_max(message: types.Message, state: FSMContext):
    if message.text != "-":
        await state.update_data(salary_max=int(message.text) if message.text.isdigit() else 0)
    await message.answer("Введите НОВУЮ ссылку (или '-'):")
    await state.set_state(EditVacancyStates.waiting_for_vacancy_link)

def fix_url(url: str) -> str:
    url = url.strip()
    if not url or url == "-": return url
    if not url.startswith(("http://", "https://")):
        if "." in url: return "https://" + url
    return url

@router.message(EditVacancyStates.waiting_for_vacancy_link)
async def edit_vac_link(message: types.Message, state: FSMContext):
    if message.text != "-":
        await state.update_data(link=fix_url(message.text))
    await message.answer("Введите НОВОЕ описание (или '-'):")
    await state.set_state(EditVacancyStates.waiting_for_vacancy_desc)

@router.message(EditVacancyStates.waiting_for_vacancy_desc)
async def edit_vac_desc(message: types.Message, state: FSMContext):
    data = await state.get_data()
    vac_id = data.pop('edit_vac_id')
    if message.text != "-":
        data['description'] = message.text
    if data:
        await update_vacancy(vac_id, **data)
        await message.answer("✅ Вакансия обновлена!", reply_markup=get_admin_keyboard())
    else:
        await message.answer("Никаких изменений не внесено.", reply_markup=get_admin_keyboard())
    await state.clear()

# --- Vacancy Addition Flow ---

@router.callback_query(F.data == "admin_add_vacancy")
async def start_add_vacancy(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название вакансии:", reply_markup=get_cancel_keyboard())
    await state.set_state(AdminStates.waiting_for_vacancy_title)
    await callback.answer()

@router.message(AdminStates.waiting_for_vacancy_title)
async def process_vac_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите название компании:")
    await state.set_state(AdminStates.waiting_for_vacancy_company)

@router.message(AdminStates.waiting_for_vacancy_company)
async def process_vac_company(message: types.Message, state: FSMContext):
    await state.update_data(company=message.text)
    await message.answer("Введите город:")
    await state.set_state(AdminStates.waiting_for_vacancy_city)

@router.message(AdminStates.waiting_for_vacancy_city)
async def process_vac_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await message.answer("Введите сферу (например, IT):")
    await state.set_state(AdminStates.waiting_for_vacancy_sphere)

@router.message(AdminStates.waiting_for_vacancy_sphere)
async def process_vac_sphere(message: types.Message, state: FSMContext):
    await state.update_data(sphere=message.text)
    await message.answer("Введите минимальную зарплату (число):")
    await state.set_state(AdminStates.waiting_for_vacancy_salary_min)

@router.message(AdminStates.waiting_for_vacancy_salary_min)
async def process_vac_salary_min(message: types.Message, state: FSMContext):
    await state.update_data(salary_min=int(message.text) if message.text.isdigit() else 0)
    await message.answer("Введите максимальную зарплату (число):")
    await state.set_state(AdminStates.waiting_for_vacancy_salary_max)

@router.message(AdminStates.waiting_for_vacancy_salary_max)
async def process_vac_salary_max(message: types.Message, state: FSMContext):
    await state.update_data(salary_max=int(message.text) if message.text.isdigit() else 0)
    await message.answer("Введите ссылку на вакансию:")
    await state.set_state(AdminStates.waiting_for_vacancy_link)

@router.message(AdminStates.waiting_for_vacancy_link)
async def process_vac_link(message: types.Message, state: FSMContext):
    await state.update_data(link=fix_url(message.text))
    await message.answer("Введите описание:")
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
