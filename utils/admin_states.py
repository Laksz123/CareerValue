from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()
    waiting_for_vacancy_title = State()
    waiting_for_vacancy_company = State()
    waiting_for_vacancy_city = State()
    waiting_for_vacancy_sphere = State()
    waiting_for_vacancy_salary_min = State()
    waiting_for_vacancy_salary_max = State()
    waiting_for_vacancy_link = State()
    waiting_for_vacancy_desc = State()

class EditVacancyStates(StatesGroup):
    waiting_for_vacancy_title = State()
    waiting_for_vacancy_company = State()
    waiting_for_vacancy_city = State()
    waiting_for_vacancy_sphere = State()
    waiting_for_vacancy_salary_min = State()
    waiting_for_vacancy_salary_max = State()
    waiting_for_vacancy_link = State()
    waiting_for_vacancy_desc = State()

class EditSettingsStates(StatesGroup):
    waiting_for_contact_link = State()
