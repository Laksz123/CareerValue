from aiogram import Router, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
from utils.db_api import increment_referral_clicks, get_setting

router = Router()

@router.message(CommandStart(deep_link=True))
async def cmd_start_deeplink(message: types.Message, command: CommandObject):
    args = (command.args or "").strip()
    if args.startswith("ref_"):
        slug = args[4:].strip()
        if slug:
            await increment_referral_clicks(slug)
    await _send_welcome(message)

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await _send_welcome(message)


async def _send_welcome(message: types.Message):
    welcome_text = await get_setting(
        "text_welcome",
        "👋 ПРИВЕТ, {name}!\n\n"
        "Хочешь узнать, сколько ты реально стоишь на рынке труда?\n\n"
        "Большинство людей занижают свою зарплату на 20–40%.\n"
        "Я рассчитаю твою рыночную стоимость и подберу подходящие вакансии за 60 секунд.\n\n"
        "👇 Нажми кнопку ниже."
    )
    text = welcome_text.format(name=message.from_user.full_name or "друг")

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(
        text="👉 Хочу узнать стоимость!", callback_data="start_quiz")
    )

    photo = FSInputFile("images/start.jpg")
    await message.answer_photo(photo=photo, caption=text, reply_markup=builder.as_markup())
