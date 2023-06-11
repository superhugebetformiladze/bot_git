import os
import pickle
import logging
import re

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup


TOKEN = "6223499018:AAGGJXrczyFYUL6ENNjQ0XSol0yj5kiw98c"
ADMIN = 408616384

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Настройка логгирования
logging.basicConfig(level=logging.INFO)

class MyState(StatesGroup):
    waiting_for_button_text = State()
    waiting_for_button_deletion = State()
    waiting_for_button_text_change = State()
    waiting_for_button_text_edit = State()
    waiting_for_button_url = State()
    waiting_for_url_deletion = State()
    waiting_for_button_text_url = State()
    waiting_for_button_deletion_url = State()

# Декоратор для проверки доступа к командам
def check_access(func):
    async def wrapper(message: types.Message, state: FSMContext, raw_state=None, **kwargs):
        # Проверяем, является ли пользователь администратором
        if message.from_user.id != ADMIN:
            await message.answer("У вас нет доступа к этой команде.")
            return
        return await func(message, state, raw_state=raw_state, **kwargs)
    return wrapper

# Проверка наличия папки "data" и её создание, если она не существует
data_folder_path = os.path.join(os.path.dirname(__file__), 'data')
if not os.path.exists(data_folder_path):
    os.makedirs(data_folder_path)

# Определите название файла данных
data_file_name = 'button_hierarchy.pickle'

# Определите путь к файлу данных
data_file_path = os.path.join(data_folder_path, data_file_name)

# Загрузка данных из файла (если они есть)
try:
    with open(data_file_path, 'rb') as file:
        button_hierarchy = pickle.load(file)
except FileNotFoundError:
    button_hierarchy = {
        'root': []
    }


@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup()

    if 'root' in button_hierarchy and button_hierarchy['root']:
        for button in button_hierarchy['root']:
            keyboard.add(button)

        # Добавляем кнопку "назад" если не на верхнем уровне
        if 'root' not in button_hierarchy:
            back_button = InlineKeyboardButton(text='Назад', callback_data='back')
            keyboard.add(back_button)
    else:
        await bot.send_message(message.chat.id, "Кнопок еще нет, выберите команду /add_button")

    await state.reset_state()
    await bot.send_message(message.chat.id, "Привет! Нажми кнопку", reply_markup=keyboard)


# добавление кнопки назад ________________________________________________________________
@dp.callback_query_handler()
async def callback_handler(call: types.CallbackQuery, state: FSMContext):
    await call.answer()

    button_placement = call.data

    if button_placement == 'back':
        # Обрабатываем нажатие кнопки "назад"
        data = await state.get_data()
        current_level = data.get('current_level', 'root')

        if current_level != 'root':
            current_button = data.get('current_button')

            # Ищем предыдущую кнопку в иерархии
            previous_level = None
            for level, buttons in button_hierarchy.items():
                for button in buttons:
                    if button.callback_data == current_button:
                        previous_level = level
                        break
                if previous_level:
                    break

            if previous_level is None:
                previous_level = 'root'

            keyboard = InlineKeyboardMarkup()

            for button in button_hierarchy[previous_level]:
                keyboard.add(button)

            # Добавляем кнопку "назад" если не на верхнем уровне
            if previous_level != 'root':
                back_button = InlineKeyboardButton(text='Назад', callback_data='back')
                keyboard.add(back_button)

            if call.message.reply_markup != keyboard:
                await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
        else:
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Нет доступных подуровней кнопок.")

        await state.set_data({'current_level': previous_level})
    else:
        if button_placement in button_hierarchy:
            keyboard = InlineKeyboardMarkup()

            for button in button_hierarchy[button_placement]:
                keyboard.add(button)

            # Добавляем кнопку "назад" если не на верхнем уровне
            if button_placement != 'root':
                back_button = InlineKeyboardButton(text='Назад', callback_data='back')
                keyboard.add(back_button)

            if call.message.reply_markup != keyboard:
                await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=keyboard)
        else:
            await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Нет доступных подуровней кнопок.")

        await state.set_data({'current_level': button_placement, 'current_button': button_placement})


# добавление кнопок ________________________________________________________________
@dp.message_handler(commands=['add_button'])
@check_access
async def add_button_handler(message: types.Message, state: FSMContext, raw_state=None, command=None):
    await bot.send_message(message.chat.id, "Введите текст для новой кнопки:")
    await MyState.waiting_for_button_text.set()

@dp.message_handler(state=MyState.waiting_for_button_text)
async def process_button_text(message: types.Message, state: FSMContext):
    button_text = message.text

    if button_text == 'Назад':
        await bot.send_message(message.chat.id, "Текст кнопки 'Назад' недопустим.")
        return

    keyboard = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(text=button_text, callback_data=button_text)
    keyboard.add(button)

    data = await state.get_data()
    current_level = data.get('current_level', 'root')

    button_hierarchy.setdefault(current_level, [])
    button_hierarchy[current_level].append(button)

    await state.reset_state()
    await bot.send_message(message.chat.id, "Инлайн кнопка успешно добавлена!", reply_markup=keyboard)

    # Сохранение данных в файл
    with open(data_file_path, 'wb') as file:
        pickle.dump(button_hierarchy, file)


# добавление ссылок ________________________________________________________________
@dp.message_handler(commands=['add_url'])
@check_access
async def add_url_button_handler(message: types.Message, state: FSMContext, raw_state=None, command=None):
    await bot.send_message(message.chat.id, "Введите текст для новой кнопки и ссылку на новой строке в одном сообщении:")
    await MyState.waiting_for_button_text_url.set()

def is_valid_url(url):
    # Проверяем, является ли текст валидным URL-адресом
    url_regex = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https://
        # domain...
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|[A-Z0-9-]+\.?|"
        r"localhost|"
        # ...or ipv4
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$", re.IGNORECASE
    )
    return re.match(url_regex, url) is not None

@dp.message_handler(state=MyState.waiting_for_button_text_url)
async def process_button_text_url(message: types.Message, state: FSMContext):
    try:
        button_text, button_url = message.text.split("\n")
    except ValueError:
        await bot.send_message(message.chat.id, "Ошибка формата ввода. Введите текст кнопки и URL, разделяя их символом новой строки.")
        return

    if button_text == 'Назад':
        await bot.send_message(message.chat.id, "Текст кнопки 'Назад' недопустим.")
        return
    
    if button_url == 'Назад':
        await bot.send_message(message.chat.id, "Текст ссылки 'Назад' недопустим.")
        return
    
    if not is_valid_url(button_url):
        await bot.send_message(message.chat.id, "Некорректный URL. Пожалуйста, введите правильный URL.")
        return

    keyboard = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(text=button_text, url=button_url)
    keyboard.add(button)

    data = await state.get_data()
    current_level = data.get('current_level', 'root')

    button_hierarchy.setdefault(current_level, [])
    button_hierarchy[current_level].append(button)

    await state.reset_state()
    await bot.send_message(message.chat.id, "Кнопка-ссылка успешно добавлена!", reply_markup=keyboard)

    # Сохранение данных в файл
    with open(data_file_path, 'wb') as file:
        pickle.dump(button_hierarchy, file)


# удаление ссылок ________________________________________________________________
def delete_button_by_name(button_name):
    for level, buttons in button_hierarchy.items():
        for button in buttons:
            if isinstance(button, types.InlineKeyboardButton) and button.text == button_name:
                buttons.remove(button)
                return True
    return False

@dp.message_handler(commands=['delete_url'])
@check_access
async def delete_url_handler(message: types.Message, state: FSMContext, raw_state=None, command=None):
    await bot.send_message(message.chat.id, "Введите название кнопки, которую вы хотите удалить:")
    await MyState.waiting_for_button_deletion_url.set()

@dp.message_handler(state=MyState.waiting_for_button_deletion_url)
async def process_button_deletion_url(message: types.Message, state: FSMContext):
    button_name = message.text

    if delete_button_by_name(button_name):
        await bot.send_message(message.chat.id, f"Кнопка '{button_name}' успешно удалена.")
    else:
        await bot.send_message(message.chat.id, f"Кнопка '{button_name}' не найдена.")

    await state.reset_state()

    # Сохранение данных в файл
    with open(data_file_path, 'wb') as file:
        pickle.dump(button_hierarchy, file)


# удалить кнопку, удалять надо с конца ________________________________________________________________
@dp.message_handler(commands=['delete_button'])
@check_access
async def delete_button_handler(message: types.Message, state: FSMContext, raw_state=None, command=None):
    await bot.send_message(message.chat.id, "Введите текст кнопки, которую вы хотите удалить:")
    await MyState.waiting_for_button_deletion.set()

@dp.message_handler(state=MyState.waiting_for_button_deletion)
async def process_button_deletion(message: types.Message, state: FSMContext):
    button_text = message.text

    data = await state.get_data()
    current_level = data.get('current_level', 'root')

    if delete_button(button_text, current_level):
        await bot.send_message(message.chat.id, f"Кнопка с текстом '{button_text}' успешно удалена.")
    else:
        await bot.send_message(message.chat.id, f"Кнопка с текстом '{button_text}' не найдена.")

    await state.reset_state()

    # Сохранение данных в файл
    with open(data_file_path, 'wb') as file:
        pickle.dump(button_hierarchy, file)

def delete_button(button_text, level):
    if level in button_hierarchy and button_hierarchy[level]:
        buttons = button_hierarchy[level]
        for button in buttons:
            if button.callback_data == button_text:
                buttons.remove(button)
                return True
        return False


# изменение кнопки ________________________________________________________________
@dp.message_handler(commands=['change_text'])
@check_access
async def change_text_handler(message: types.Message, state: FSMContext, raw_state=None, command=None):
    await bot.send_message(message.chat.id, "Введите текст кнопки, для которой хотите изменить текст:")
    await MyState.waiting_for_button_text_change.set()

@dp.message_handler(state=MyState.waiting_for_button_text_change)
async def process_button_text_change(message: types.Message, state: FSMContext):
    button_text = message.text

    data = await state.get_data()
    current_level = data.get('current_level', 'root')

    if current_level in button_hierarchy and button_hierarchy[current_level]:
        buttons = button_hierarchy[current_level]
        for button in buttons:
            if button.callback_data == button_text:
                await bot.send_message(message.chat.id, "Введите новый текст для кнопки:")
                await MyState.waiting_for_button_text_edit.set()
                await state.update_data(edit_button=button, current_level=current_level)
                break
        else:
            await bot.send_message(message.chat.id, f"Кнопка с текстом '{button_text}' не найдена.")
    else:
        await bot.send_message(message.chat.id, f"Кнопка с текстом '{button_text}' не найдена.")

@dp.message_handler(state=MyState.waiting_for_button_text_edit)
async def process_button_text_edit(message: types.Message, state: FSMContext):
    button_text = message.text

    data = await state.get_data()
    edit_button = data.get('edit_button')
    current_level = data.get('current_level', 'root')
    if edit_button:
        await update_button_text(edit_button, button_text)
        await state.reset_state()
        await bot.send_message(message.chat.id, f"Кнопка успешно отредактирована! Новый текст: {button_text}")
    else:
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton(text=button_text, callback_data=button_text)
        keyboard.add(button)

        button_hierarchy.setdefault(current_level, [])
        button_hierarchy[current_level].append(button)

        await state.reset_state()
        await bot.send_message(message.chat.id, "Инлайн кнопка успешно добавлена!", reply_markup=keyboard)

    # Сохранение данных в файл
    with open(data_file_path, 'wb') as file:
        pickle.dump(button_hierarchy, file)

async def update_button_text(button, new_text):
    button.text = new_text

    # Обновление текста кнопки в button_hierarchy
    for level, buttons in button_hierarchy.items():
        for index, b in enumerate(buttons):
            if b.callback_data == button.callback_data:
                button_hierarchy[level][index] = button
                break

    # Сохранение данных в файл
    with open(data_file_path, 'wb') as file:
        pickle.dump(button_hierarchy, file)


# назад ________________________________________________________________
@dp.message_handler(commands=['back'])
async def back_button_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_level = data.get('current_level', 'root')

    if current_level != 'root':
        current_button = data.get('current_button')

        # Ищем предыдущую кнопку в иерархии
        previous_level = None
        for level, buttons in button_hierarchy.items():
            for button in buttons:
                if button.callback_data == current_button:
                    previous_level = level
                    break
            if previous_level:
                break

        if previous_level is None:
            previous_level = 'root'

        keyboard = InlineKeyboardMarkup()

        for button in button_hierarchy[previous_level]:
            keyboard.add(button)

        # Добавляем кнопку "назад" если не на верхнем уровне
        if previous_level != 'root':
            back_button = InlineKeyboardButton(text='Назад', callback_data='back')
            keyboard.add(back_button)

        await bot.send_message(message.chat.id, "Привет! Нажми кнопку", reply_markup=keyboard)
        await state.set_data({'current_level': previous_level})
    else:
        await bot.send_message(message.chat.id, "Вы уже на верхнем уровне иерархии кнопок.")


# удалить все________________________________________________________________________________
@dp.message_handler(commands=['reset'])
@check_access
async def reset_handler(message: types.Message, state: FSMContext, raw_state=None, command=None):
    global button_hierarchy

    button_hierarchy = {
        'root': []
    }

    # Удаляем файл данных, если он существует
    if os.path.exists(data_file_path):
        os.remove(data_file_path)

    await message.reply("Иерархия кнопок сброшена.")


# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
