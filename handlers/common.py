from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="👉 Хочу узнать стоимость!", callback_data="start_quiz")
    )
    
    text = (
        f"👋 ПРИВЕТ, {message.from_user.full_name}!\n\n"
        "Хочешь узнать, сколько ты реально стоишь на рынке труда?\n\n"
        "Большинство людей занижают свою зарплату на 20–40%.\n"
        "Я рассчитаю твою рыночную стоимость и подберу подходящие вакансии за 60 секунд.\n\n"
        "👇 Нажми кнопку ниже."
    )
    
    photo = FSInputFile("images/start.jpg")
    await message.answer_photo(photo=photo, caption=text, reply_markup=builder.as_markup())
