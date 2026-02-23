from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import FSInputFile, InputMediaPhoto
from utils.states import QuizStates
from utils.db_api import get_or_create_user, update_user_survey, get_vacancies, get_setting
import random
import asyncio

router = Router()

@router.callback_query(F.data == "start_quiz")
async def start_quiz(callback: types.CallbackQuery, state: FSMContext):
    await get_or_create_user(
        callback.from_user.id, 
        callback.from_user.username, 
        callback.from_user.full_name
    )
    
    await callback.message.answer(
        "🚀 Отлично!\n\n"
        "Чтобы я рассчитал твою стоимость и подобрал подходящие вакансии, "
        "ответь на 3 коротких вопроса.\n\n"
        "⏳ Это займёт меньше 60 секунд\n"
        "🎯 Ты получишь персональную подборку"
    )
    
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="Москва"), types.KeyboardButton(text="Санкт-Петербург"))
    builder.row(types.KeyboardButton(text="Екатеринбург"), types.KeyboardButton(text="Новосибирск"))
    builder.row(types.KeyboardButton(text="🌍 Другой"))
    
    await callback.message.answer(
        "📍 В каком городе ты ищешь работу?",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(QuizStates.waiting_for_city)
    await callback.answer()

@router.message(QuizStates.waiting_for_city)
async def process_city(message: types.Message, state: FSMContext):
    if message.text == "🌍 Другой":
        await message.answer("Напиши название своего города:")
        await state.set_state(QuizStates.waiting_for_custom_city)
        return

    await state.update_data(city=message.text)
    await ask_sphere(message, state)

@router.message(QuizStates.waiting_for_custom_city)
async def process_custom_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await ask_sphere(message, state)

async def ask_sphere(message: types.Message, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="💻 IT"), types.KeyboardButton(text="💬 Продажи"))
    builder.row(types.KeyboardButton(text="📦 Склад / производство"), types.KeyboardButton(text="🚚 Логистика"))
    builder.row(types.KeyboardButton(text="🔎 Другое"))
    
    await message.answer(
        "💼 В какой сфере ты работаешь или хочешь работать?",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(QuizStates.waiting_for_sphere)

@router.message(QuizStates.waiting_for_sphere)
async def process_sphere(message: types.Message, state: FSMContext):
    if message.text == "🔎 Другое":
        await message.answer("Напиши свою сферу деятельности:")
        await state.set_state(QuizStates.waiting_for_custom_sphere)
        return
        
    await state.update_data(sphere=message.text)
    await ask_experience(message, state)

@router.message(QuizStates.waiting_for_custom_sphere)
async def process_custom_sphere(message: types.Message, state: FSMContext):
    await state.update_data(sphere=message.text)
    await ask_experience(message, state)

async def ask_experience(message: types.Message, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="❌ Без опыта"))
    builder.row(types.KeyboardButton(text="🔄 До 1 года"))
    builder.row(types.KeyboardButton(text="✅ 1–3 года"))
    
    await message.answer(
        "📈 Сколько у тебя опыта?",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )
    await state.set_state(QuizStates.waiting_for_experience)

@router.message(QuizStates.waiting_for_experience)
async def process_experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text)
    data = await state.get_data()
    
    # Start imitation of analysis with image
    photo_analysis = FSInputFile(r"c:\Users\345643q6t\Desktop\images\analys.jpg")
    analysis_msg = await message.answer_photo(
        photo=photo_analysis, 
        caption="🧠 Анализирую рынок…", 
        reply_markup=types.ReplyKeyboardRemove()
    )
    
    # Helper to safely edit caption
    async def safe_edit_caption(msg, new_caption):
        try:
            await message.bot.edit_message_caption(
                chat_id=msg.chat.id,
                message_id=msg.message_id,
                caption=new_caption
            )
        except Exception:
            pass # Ignore errors during intermediate status updates

    await asyncio.sleep(random.uniform(0.7, 1.2))
    await safe_edit_caption(analysis_msg, "📊 Сравниваю с 2 000+ вакансиями…")
    
    await asyncio.sleep(random.uniform(0.7, 1.2))
    await safe_edit_caption(analysis_msg, "💰 Считаю твой потенциал…")
    
    await asyncio.sleep(random.uniform(1.0, 1.5))
    
    # Calculate Result (Placeholder logic for now)
    base_salary = 80000
    if "IT" in data['sphere']: base_salary = 120000
    elif "Продажи" in data['sphere']: base_salary = 90000
    
    if "1–3 года" in data['experience']: multiplier = 1.4
    elif "До 1 года" in data['experience']: multiplier = 1.1
    else: multiplier = 0.8
    
    market_value = int(base_salary * multiplier)
    potential_value = int(market_value * 1.2)
    undervalued = 20
    career_index = random.randint(70, 85)

    result_text = (
        f"💰 Твоя рыночная стоимость: {market_value:,} ₽\n\n"
        f"Но по текущим данным рынка ты можешь выйти на {potential_value:,} ₽ уже сейчас.\n\n"
        f"Ты недооцениваешь себя примерно на {undervalued}%.\n\n"
        f"📊 Твой карьерный индекс: {career_index} / 100\n\n"
        f"До уровня {potential_value:,} ₽ тебе не хватает:\n"
        "— более смелой планки по зарплате\n"
        "— откликов на вакансии уровнем выше"
    ).replace(",", " ")
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🔥 Показать вакансии", callback_data="show_vacancies"))
    builder.row(types.InlineKeyboardButton(text=f"📈 Как выйти на {potential_value:,} ₽?".replace(",", " "), callback_data="how_to_increase"))

    await update_user_survey(
        message.from_user.id,
        city=data['city'],
        sphere=data['sphere'],
        experience=data['experience'],
        market_value=market_value,
        test_completed=True
    )

    # Change image to result and update caption
    photo_result = FSInputFile(r"c:\Users\345643q6t\Desktop\images\result.jpg")
    try:
        await message.bot.edit_message_media(
            chat_id=analysis_msg.chat.id,
            message_id=analysis_msg.message_id,
            media=InputMediaPhoto(media=photo_result, caption=result_text),
            reply_markup=builder.as_markup()
        )
    except Exception:
        # Fallback if media edit fails
        await message.answer_photo(
            photo=photo_result,
            caption=result_text,
            reply_markup=builder.as_markup()
        )
    
    await state.clear()


def normalize_url(url: str) -> str:
    if not url:
        return "https://t.me"
    url = url.strip()
    if url.startswith(("http://", "https://")):
        return url
    # If it looks like a relative path or just a string, fallback to a safe URL
    return "https://t.me"

@router.callback_query(F.data == "show_vacancies")
async def show_vacancies(callback: types.CallbackQuery):
    photo_vacancies = FSInputFile(r"c:\Users\345643q6t\Desktop\images\list of vacancies.jpg")
    await callback.message.answer_photo(
        photo=photo_vacancies,
        caption="🔎 Ищу подходящие вакансии...\nЭто может занять немного времени ☕"
    )
    
    vacs = await get_vacancies(3)
    
    if not vacs:
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="🏠 Вернуться в главное меню", callback_data="back_to_main"))
        await callback.message.answer(
            "К сожалению, подходящих вакансий пока нет. Загляните позже!",
            reply_markup=builder.as_markup()
        )
        await callback.answer()
        return

    for i, v in enumerate(vacs):
        # Typing action + delay to simulate search
        await callback.message.bot.send_chat_action(
            chat_id=callback.message.chat.id, action="typing"
        )
        await asyncio.sleep(random.uniform(5, 10))

        salary_str = f"{v.salary_min or ''} - {v.salary_max or ''} ₽"
        text = (
            f"🔹 {v.title}\n"
            f"🏢 Компания: {v.company}\n"
            f"📍 Город: {v.city}\n"
            f"💰 Зарплата: {salary_str}\n"
            f"📝 Кратко: {v.description[:100]}...\n\n"
        )
        builder = InlineKeyboardBuilder()
        valid_url = normalize_url(v.link)
        builder.row(types.InlineKeyboardButton(text="👉 Подробнее", url=valid_url))
        await callback.message.answer(text, reply_markup=builder.as_markup())
    
    # "Back to main menu" button after all vacancies
    back_builder = InlineKeyboardBuilder()
    back_builder.row(types.InlineKeyboardButton(text="🏠 Вернуться в главное меню", callback_data="back_to_main"))
    await callback.message.answer(
        "👆 Вот что я нашёл для тебя!",
        reply_markup=back_builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "how_to_increase")
async def how_to_increase(callback: types.CallbackQuery):
    contact_link = await get_setting("contact_link", "https://t.me")
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📞 Связаться", url=contact_link))
    builder.row(types.InlineKeyboardButton(text="🏠 Вернуться в главное меню", callback_data="back_to_main"))
    await callback.message.answer(
        "📈 Чтобы выйти на желаемый уровень дохода, рекомендуем:\n\n"
        "1. Обновить резюме под конкретную роль.\n"
        "2. Пройти аудит текущих навыков.\n"
        "3. Подготовиться к техническому интервью.\n\n"
        "📞 Хочешь бесплатную консультацию? Нажми кнопку ниже 👇",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="👉 Хочу узнать стоимость!", callback_data="start_quiz")
    )
    
    text = (
        f"👋 ПРИВЕТ, {callback.from_user.full_name}!\n\n"
        "Хочешь узнать, сколько ты реально стоишь на рынке труда?\n\n"
        "Большинство людей занижают свою зарплату на 20–40%.\n"
        "Я рассчитаю твою рыночную стоимость и подберу подходящие вакансии за 60 секунд.\n\n"
        "👇 Нажми кнопку ниже."
    )
    
    photo = FSInputFile(r"c:\Users\345643q6t\Desktop\images\start.jpg")
    await callback.message.answer_photo(photo=photo, caption=text, reply_markup=builder.as_markup())
    await callback.answer()
