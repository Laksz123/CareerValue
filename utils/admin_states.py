from aiogram.fsm.state import State, StatesGroup

class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()
    waiting_for_vacancy_post = State()

class EditSettingsStates(StatesGroup):
    waiting_for_contact_link = State()


class EditDelaysStates(StatesGroup):
    waiting_for_loading_delays = State()
    waiting_for_vacancy_delays = State()
    waiting_for_funnel_delay = State()


class EditTextsStates(StatesGroup):
    waiting_for_text_value = State()


class ReferralLinkStates(StatesGroup):
    waiting_for_link_name = State()
