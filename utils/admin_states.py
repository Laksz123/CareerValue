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
    waiting_for_edit_value = State()  # generic: edit_vac_id + edit_field in state

class EditSettingsStates(StatesGroup):
    waiting_for_contact_link = State()


class EditDelaysStates(StatesGroup):
    waiting_for_loading_delays = State()
    waiting_for_vacancy_delays = State()


class EditTextsStates(StatesGroup):
    waiting_for_text_value = State()
