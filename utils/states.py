from aiogram.fsm.state import State, StatesGroup

class QuizStates(StatesGroup):
    waiting_for_city = State()
    waiting_for_custom_city = State()
    waiting_for_sphere = State()
    waiting_for_custom_sphere = State()
    waiting_for_experience = State()
