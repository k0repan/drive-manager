from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from googleapiclient.errors import HttpError

from google_api import API
from states import UploadForm
from kb import *

from pathlib import Path


router = Router()

api = API()
api.init_by_file()


@router.callback_query(Callback.filter(F.path == "to_about"))
async def about_query(query: CallbackQuery, callback_data: Callback):    
    about = api.about()
    await query.message.edit_text(about, reply_markup=build_keyboard("back"))


@router.callback_query(Callback.filter(F.path == "to_main"))
async def main_query(query: CallbackQuery, callback_data: Callback, state: FSMContext):    
    api.files = None
    api.names = None
    await state.clear()

    await query.message.edit_text("Чем я могу помочь тебе сегодня?", reply_markup=build_keyboard("main"))


@router.callback_query(Callback.filter(F.path == "to_view"))
async def view_query(query: CallbackQuery, callback_data: Callback):
    files, current, total = api.through_the_files()
    if not files:
        await query.message.edit_text("На диске нет файлов...", reply_markup=build_keyboard("back"))
    else:
        await query.message.edit_text(f"Выберите желаемый файл ({current}/{total})", reply_markup=build_keyboard_for_files(files, callback_data.path, "view", "view"))


@router.callback_query(CallbackView.filter(F.path == "view"))
async def view_file(query: CallbackQuery, callback_data: CallbackView):
    await query.message.edit_text(callback_data.link.replace("https", api.link_base), reply_markup=build_keyboard("back"))


@router.callback_query(Callback.filter(F.path == "to_upload"))
async def upload_query(query: CallbackQuery, callback_data: Callback, state: FSMContext):    
    await state.set_state(UploadForm.send_file)
    await query.message.edit_text("Пожалуйста, пришли файл для загрузки.", reply_markup=build_keyboard("back"))


@router.message(UploadForm.send_file)
async def upload_file(msg: Message, state: FSMContext):
    file_id = msg.document.file_id
    file_name = msg.document.file_name
    file = await msg.bot.get_file(file_id)
    file_path = file.file_path

    await msg.bot.download_file(file_path, f"download/{file_name}")
    api.upload(file_name, msg.document.mime_type)
    Path.unlink(f"download/{file_name}")

    await state.clear()
    await msg.answer("файл был успешно загружен!", reply_markup=build_keyboard("back"))


@router.callback_query(Callback.filter(F.path == "to_download"))
async def download_query(query: CallbackQuery, callback_data: Callback):
    files, current, total = api.through_the_files()
    if not files:
        await query.message.edit_text("На диске нет файлов...", reply_markup=build_keyboard("back"))
    else:
        await query.message.edit_text(f"Выберите желаемый файл ({current}/{total})", reply_markup=build_keyboard_for_files(files, callback_data.path, "download"))


@router.callback_query(CallbackFile.filter(F.path == "download"))
async def download_file(query: CallbackQuery, callback_data: CallbackFile):
    await query.answer("Скачивание началось...")
    api.download(callback_data.file_id)
    name = api.names[callback_data.file_id]
    file = FSInputFile(f"download/{name}", name)

    await query.message.answer_document(file)
    Path.unlink(f"download/{name}")


@router.callback_query(Callback.filter(F.path == "to_delete"))
async def delete_query(query: CallbackQuery, callback_data: Callback):
    files, current, total = api.through_the_files(True)
    if not files:
        await query.message.edit_text("На диске нет файлов...", reply_markup=build_keyboard("back"))
    else:
        await query.message.edit_text(f"Выберите желаемый файл ({current}/{total})", reply_markup=build_keyboard_for_files(files, callback_data.path, "delete"))


@router.callback_query(CallbackFile.filter(F.path == "delete"))
async def delete_file(query: CallbackQuery, callback_data: CallbackFile):
    try:
        api.delete(callback_data.file_id)
        await query.message.edit_text("Файл был успешно удалён!", reply_markup=build_keyboard("back"))

    except HttpError:
        await query.message.edit_text("У вас недостаточно прав для удаления этого файла.", reply_markup=build_keyboard("back"))


@router.callback_query(Callback.filter(F.path == "to_trash"))
async def trash_query(query: CallbackQuery, callback_data: Callback):
    files, current, total = api.through_the_files(True)
    if not files:
        await query.message.edit_text("На диске нет файлов...", reply_markup=build_keyboard("back"))
    else:
        await query.message.edit_text(f"Выберите желаемый файл ({current}/{total})", reply_markup=build_keyboard_for_files(files, callback_data.path, "trash"))


@router.callback_query(CallbackFile.filter(F.path == "trash"))
async def trash_file(query: CallbackQuery, callback_data: CallbackFile):
    api.trash(callback_data.file_id)
    await query.message.edit_text("Файл был перемещён в корзину!", reply_markup=build_keyboard("back"))


@router.message(Command("start"))
async def start_handler(msg: Message, state: FSMContext):
    api.files = None
    api.names = None
    await state.clear()

    await msg.answer("Добро пожаловать! Я - твой личный менеджер Google Drive.", reply_markup=build_keyboard("main"))


@router.message()
async def message_handler(msg: Message):
    await msg.answer("Прости, я не знаю такой команды...")