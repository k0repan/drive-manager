from aiogram.fsm.state import State, StatesGroup


class UploadForm(StatesGroup):
    send_file = State()