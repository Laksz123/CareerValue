from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.types import FSInputFile, InputMediaPhoto, MessageEntity
from utils.states import QuizStates
from utils.db_api import get_or_create_user, update_user_survey, get_vacancy_posts, get_setting
from typing import Set, Tuple
import json
import random
import asyncio

router = Router()

@router.callback_query(F.data == "start_quiz")
async def start_quiz(callback: types.CallbackQuery, state: FSMContext):
    chat_id = callback.message.chat.id
    msg_id = callback.message.message_id
    if not _acquire_callback(chat_id, msg_id):
        await callback.answer()
        return
    try:
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
    finally:
        _release_callback(chat_id, msg_id)

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
    
    # Start imitation of analysis with animation
    anim_analysis = FSInputFile("images/analys.gif")
    analysis_msg = await message.answer_animation(
        animation=anim_analysis,
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
            pass

    loading_min = float(await get_setting("delay_loading_min", "0.7"))
    loading_max = float(await get_setting("delay_loading_max", "1.2"))
    text_1 = await get_setting("text_loading_1", "📊 Сравниваю с 2 000+ вакансиями…")
    text_2 = await get_setting("text_loading_2", "💰 Считаю твой потенциал…")

    await asyncio.sleep(random.uniform(loading_min, loading_max))
    await safe_edit_caption(analysis_msg, text_1)

    await asyncio.sleep(random.uniform(loading_min, loading_max))
    await safe_edit_caption(analysis_msg, text_2)

    await asyncio.sleep(random.uniform(loading_min, loading_max))
    
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

    result_template = await get_setting(
        "text_result",
        "💰 Твоя рыночная стоимость: {market_value} ₽\n\n"
        "Но по текущим данным рынка ты можешь выйти на {potential_value} ₽ уже сейчас.\n\n"
        "Ты недооцениваешь себя примерно на {undervalued}%.\n\n"
        "📊 Твой карьерный индекс: {career_index} / 100\n\n"
        "До уровня {potential_value} ₽ тебе не хватает:\n"
        "— более смелой планки по зарплате\n"
        "— откликов на вакансии уровнем выше"
    )
    result_text = result_template.format(
        market_value=f"{market_value:,}".replace(",", " "),
        potential_value=f"{potential_value:,}".replace(",", " "),
        career_index=career_index,
        undervalued=undervalued,
    )
    
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

    # Delete loading message and send result as new message
    try:
        await message.bot.delete_message(chat_id=analysis_msg.chat.id, message_id=analysis_msg.message_id)
    except Exception:
        pass
    photo_result = FSInputFile("images/result.jpg")
    await message.answer_photo(
        photo=photo_result,
        caption=result_text,
        reply_markup=builder.as_markup()
    )
    await state.clear()


# Protection from double-click: in-flight processing keys
_processing_callbacks: Set[Tuple[int, int]] = set()


def _acquire_callback(chat_id: int, message_id: int) -> bool:
    key = (chat_id, message_id)
    if key in _processing_callbacks:
        return False
    _processing_callbacks.add(key)
    return True


def _release_callback(chat_id: int, message_id: int):
    _processing_callbacks.discard((chat_id, message_id))


@router.callback_query(F.data == "show_vacancies")
async def show_vacancies(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    msg_id = callback.message.message_id
    if not _acquire_callback(chat_id, msg_id):
        await callback.answer()
        return
    try:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.answer()

        vac_delay_min = float(await get_setting("delay_vacancy_min", "1.5"))
        vac_delay_max = float(await get_setting("delay_vacancy_max", "3.0"))

        vacancy_intro = await get_setting(
            "text_vacancy_intro",
            "🔎 Нашёл {count} подходящих вакансий выше твоей текущей планки.\n\n"
        )
        no_vacancies_text = await get_setting(
            "text_no_vacancies",
            "К сожалению, подходящих вакансий пока нет. Загляните позже!"
        )

        posts = await get_vacancy_posts(3)

        if not posts:
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(text="🏠 Вернуться в главное меню", callback_data="back_to_main"))
            await callback.message.answer(no_vacancies_text, reply_markup=builder.as_markup())
        else:
            intro = vacancy_intro.replace("{count}", str(len(posts)))
            await callback.message.answer(intro)

            for post in posts:
                await asyncio.sleep(random.uniform(vac_delay_min, vac_delay_max))
                entities = []
                if post.entities_json:
                    entities = [MessageEntity.model_validate(e) for e in json.loads(post.entities_json)]
                if post.content_type == "photo":
                    await callback.message.bot.send_photo(
                        chat_id=callback.message.chat.id,
                        photo=post.photo_file_id,
                        caption=post.text,
                        caption_entities=entities if entities else None,
                    )
                else:
                    await callback.message.answer(
                        post.text,
                        entities=entities if entities else None,
                    )

            back_builder = InlineKeyboardBuilder()
            back_builder.row(types.InlineKeyboardButton(text="🏠 Вернуться в главное меню", callback_data="back_to_main"))
            await callback.message.answer("👆 Вот что я нашёл для тебя!", reply_markup=back_builder.as_markup())
    finally:
        _release_callback(chat_id, msg_id)

@router.callback_query(F.data == "how_to_increase")
async def how_to_increase(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    msg_id = callback.message.message_id
    if not _acquire_callback(chat_id, msg_id):
        await callback.answer()
        return
    try:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.answer()

        how_text = await get_setting(
            "text_how_to_increase",
            "📈 Чтобы выйти на желаемый уровень дохода, рекомендуем:\n\n"
            "1. Обновить резюме под конкретную роль.\n"
            "2. Пройти аудит текущих навыков.\n"
            "3. Подготовиться к техническому интервью.\n\n"
            "📞 Хочешь бесплатную консультацию? Нажми кнопку ниже 👇"
        )
        contact_link = await get_setting("contact_link", "https://t.me")
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="📞 Связаться", url=contact_link))
        builder.row(types.InlineKeyboardButton(text="🏠 Вернуться в главное меню", callback_data="back_to_main"))

        photo = FSInputFile("images/result.jpg")
        try:
            await callback.message.bot.edit_message_media(
                chat_id=chat_id,
                message_id=msg_id,
                media=InputMediaPhoto(media=photo, caption=how_text),
                reply_markup=builder.as_markup()
            )
        except Exception:
            await callback.message.answer_photo(
                photo=photo,
                caption=how_text,
                reply_markup=builder.as_markup()
            )
    finally:
        _release_callback(chat_id, msg_id)

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    msg_id = callback.message.message_id
    if not _acquire_callback(chat_id, msg_id):
        await callback.answer()
        return
    try:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        await callback.answer()

        welcome_text = await get_setting(
            "text_welcome",
            "👋 ПРИВЕТ, {name}!\n\n"
            "Хочешь узнать, сколько ты реально стоишь на рынке труда?\n\n"
            "Большинство людей занижают свою зарплату на 20–40%.\n"
            "Я рассчитаю твою рыночную стоимость и подберу подходящие вакансии за 60 секунд.\n\n"
            "👇 Нажми кнопку ниже."
        )
        text = welcome_text.format(name=callback.from_user.full_name or "друг")

        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(
            text="👉 Хочу узнать стоимость!", callback_data="start_quiz")
        )

        photo = FSInputFile("images/start.jpg")
        try:
            await callback.message.bot.edit_message_media(
                chat_id=chat_id,
                message_id=msg_id,
                media=InputMediaPhoto(media=photo, caption=text),
                reply_markup=builder.as_markup()
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer_photo(
                photo=photo,
                caption=text,
                reply_markup=builder.as_markup()
            )
    finally:
        _release_callback(chat_id, msg_id)
