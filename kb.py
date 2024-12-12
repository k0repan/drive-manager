from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
import json

IKB = InlineKeyboardBuilder


with open("keyboards.json", "r", encoding="utf-8") as f:
    keyboards = json.load(f)


class Callback(CallbackData, prefix="callback"):
    path: str


class CallbackFile(CallbackData, prefix="f"):
    path: str
    file_id: str


class CallbackView(CallbackData, prefix="v"):
    path: str
    link: str


def build_keyboard(command: str):
    builder = IKB()
    builder.adjust(2)

    for kb in keyboards[command]:
        builder.button(text=kb["text"], callback_data=Callback(path=kb["path"]))

    builder.adjust(2, repeat=True)
    return builder.as_markup()


def build_keyboard_for_files(files: list[dict], path: str, action: str = "", type: str = "file"):
    builder = IKB()

    if type == "file":
        for file in files:
            builder.button(text=file["name"], callback_data=CallbackFile(path=action, file_id=file["id"]))
    elif type == "view":
        for file in files:
            builder.button(text=file["name"], callback_data=CallbackView(path=action, link=file["webViewLink"].replace("https://drive.google.com/file/d/", "https")))

    builder.button(text="Отмена", callback_data=Callback(path="to_main"))
    builder.button(text="Далее", callback_data=Callback(path=path))


    builder.adjust(2, repeat=True)
    return builder.as_markup()